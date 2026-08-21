"""
Voice server with session state — tracks language, conversation history,
and stage per call, keyed by call_sid.
"""

import asyncio
import websockets
import json
import base64
from contextlib import suppress
import sys
import os
import urllib.error
import urllib.request
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from interfaces import transcribe, synthesize

SAMPLE_RATE = 8000       # confirm against your Voicebot applet's config
SILENCE_TIMEOUT = 2.5    # seconds of actual quiet before we treat it as "caller stopped talking"
SILENCE_RMS_THRESHOLD = 300  # tune this — lower catches quieter speech, higher ignores background noise
CHUNK_SIZE = 1600        # 100 ms at 8 kHz, 16-bit mono

sessions = {}
# each session looks like:
# {
#   "buffer": [...],
#   "last_audio_time": float,
#   "stream_sid": str,
#   "language": str | None,       # locked in once confidently detected
#   "stage": "greeting" | "in_conversation",
#   "history": [ {"caller": str, "ai": str}, ... ],
# }


def make_hold_music() -> bytes:
    """Create a brief, unobtrusive hold melody as 8 kHz signed 16-bit PCM."""
    notes = [
        (523.25, 0.18),  # C5
        (659.25, 0.18),  # E5
        (783.99, 0.28),  # G5
        (0, 0.18),       # rest
        (659.25, 0.18),
        (523.25, 0.35),
        (0, 0.25),
    ]
    parts = []
    for frequency, duration in notes:
        samples = int(SAMPLE_RATE * duration)
        if frequency == 0:
            parts.append(np.zeros(samples, dtype=np.float32))
            continue

        time_axis = np.arange(samples, dtype=np.float32) / SAMPLE_RATE
        envelope = np.minimum(
            np.linspace(0, 1, samples, dtype=np.float32) * 12,
            np.linspace(1, 0, samples, dtype=np.float32) * 12,
        )
        parts.append(0.12 * np.sin(2 * np.pi * frequency * time_axis) * envelope)

    return (np.concatenate(parts).clip(-1, 1) * 32767).astype(np.int16).tobytes()


HOLD_MUSIC_PCM = make_hold_music()


async def play_hold_music(websocket, stream_sid):
    """Loop the hold melody until the RAG and TTS work for a turn is complete."""
    print(f"[{stream_sid}] Playing hold music while preparing the response")
    try:
        while True:
            await send_pcm(websocket, stream_sid, HOLD_MUSIC_PCM)
    except asyncio.CancelledError:
        print(f"[{stream_sid}] Hold music stopped")
        raise


def new_session(stream_sid):
    return {
        "buffer": [],
        "has_speech": False,
        "full_recording": [],          # keeps every chunk for the whole call, for saving to a .wav afterward
        "last_audio_time": asyncio.get_event_loop().time(),
        "stream_sid": stream_sid,
        "language": None,
        "language_attempts": 0,        # how many low-confidence tries before we escalate to DTMF
        "awaiting_dtmf": False,        # True once we've asked the caller to press a key
        "stage": "greeting",
        "history": [],
    }


# Map keypad digits to language codes — extend as you support more languages
DTMF_LANGUAGE_MAP = {
    "1": "ta",   # Tamil
    "2": "hi",   # Hindi
    "3": "en",   # English
}

LOW_CONFIDENCE_THRESHOLD = 0.6
MAX_LANGUAGE_ATTEMPTS = 2  # after this many low-confidence tries, fall back to DTMF


async def monitor_silence(websocket, call_sid):
    while call_sid in sessions:
        await asyncio.sleep(0.5)
        session = sessions.get(call_sid)
        if not session:
            break
        idle_for = asyncio.get_event_loop().time() - session["last_audio_time"]
        if session["buffer"] and session["has_speech"] and idle_for > SILENCE_TIMEOUT:
            audio_bytes = b"".join(session["buffer"])
            session["buffer"] = []
            session["has_speech"] = False
            print(f"[{call_sid}] Silence detected — {len(audio_bytes)} bytes buffered. Processing...")
            await process_turn(websocket, call_sid, audio_bytes)


async def process_turn(websocket, call_sid, audio_bytes):
    session = sessions[call_sid]

    # If we're waiting on a keypad language selection, don't try to transcribe —
    # DTMF is handled separately in the handler's dtmf branch.
    if session["awaiting_dtmf"]:
        return

    result = await asyncio.to_thread(transcribe, audio_bytes)
    caller_text = result["text"]

    if session["language"] is None:
        if result["confidence"] >= LOW_CONFIDENCE_THRESHOLD:
            session["language"] = result["language"]
            print(f"[{call_sid}] Language locked to: {session['language']} (confidence {result['confidence']})")
        else:
            session["language_attempts"] += 1
            print(f"[{call_sid}] Low confidence ({result['confidence']}), "
                  f"attempt {session['language_attempts']}/{MAX_LANGUAGE_ATTEMPTS}")

            if session["language_attempts"] < MAX_LANGUAGE_ATTEMPTS:
                # Try again — play a short multilingual prompt asking them to repeat themselves
                prompt_audio = await asyncio.to_thread(
                    synthesize,
                    "Please say that again. Tamil, Hindi, or English is fine.",
                    "en"  # neutral fallback language for the prompt itself
                )
                await send_pcm(websocket, session["stream_sid"], prompt_audio)
                print(f"[{call_sid}] Played multilingual retry prompt, waiting for next attempt")
                return  # don't generate a response yet — we're still figuring out the language
            else:
                # Give up on speech detection, fall back to keypad
                session["awaiting_dtmf"] = True
                prompt_audio = await asyncio.to_thread(
                    synthesize,
                    "Press 1 for Tamil. Press 2 for Hindi. Press 3 for English.",
                    "en"
                )
                await send_pcm(websocket, session["stream_sid"], prompt_audio)
                print(f"[{call_sid}] Escalated to DTMF fallback, waiting for keypress")
                return

    language = session["language"]
    print(f"[{call_sid}] Caller said: '{caller_text}' (lang={language}, confidence={result['confidence']})")

    hold_music_task = asyncio.create_task(
        play_hold_music(websocket, session["stream_sid"])
    )

    try:
        response_text = await build_response(session, caller_text, call_sid)
        print(f"[{call_sid}] Team B response received ({len(response_text)} characters). Requesting Sarvam TTS...")

        session["history"].append({"caller": caller_text, "ai": response_text})
        session["stage"] = "in_conversation"

        response_audio = await asyncio.to_thread(synthesize, response_text, language)
        print(f"[{call_sid}] Sarvam returned {len(response_audio)} PCM bytes. Sending to caller...")
    finally:
        hold_music_task.cancel()
        with suppress(asyncio.CancelledError):
            await hold_music_task

    await send_pcm(websocket, session["stream_sid"], response_audio)

    print(f"[{call_sid}] Turn {len(session['history'])} complete. "
          f"History so far: {[t['caller'] for t in session['history']]}")


async def build_response(session, caller_text, call_sid):
    """
    Calls Team B's /converse endpoint. Currently pointed at a local stub —
    once Team B gives you a real URL, just change TEAM_B_CONVERSE_URL below.
    Nothing else in this file needs to change.
    """
    return await asyncio.to_thread(call_converse, text=caller_text, language=session["language"], session_id=call_sid)


TEAM_B_CONVERSE_URL = os.getenv(
    "TEAM_B_CONVERSE_URL",
    "https://handclap-bonelike-jeeringly.ngrok-free.dev/converse",
)
TEAM_B_STATE = os.getenv("TEAM_B_STATE")
TEAM_B_DISTRICT = os.getenv("TEAM_B_DISTRICT")


def call_converse(text, language, session_id):
    """
    Call Team B's RAG + LLM service and return its safe user-facing response.
    """
    payload = {
        "text": text,
        "language": language,
        "session_id": session_id,
    }
    if TEAM_B_STATE:
        payload["state"] = TEAM_B_STATE
    if TEAM_B_DISTRICT:
        payload["district"] = TEAM_B_DISTRICT

    request = urllib.request.Request(
        TEAM_B_CONVERSE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        print(f"[{session_id}] Calling Team B RAG endpoint...")
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
        response_text = data.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise ValueError("Team B response did not contain a non-empty 'response' field")
        return response_text
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, json.JSONDecodeError) as error:
        print(f"[{session_id}] Team B call failed ({error})")
        return "Sorry, I'm having trouble reaching our information system right now."


async def send_pcm(websocket, stream_sid, pcm_bytes):
    for i in range(0, len(pcm_bytes), CHUNK_SIZE):
        chunk = pcm_bytes[i:i + CHUNK_SIZE]
        msg = {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode()},
        }
        await websocket.send(json.dumps(msg))
        # Send in real time.  Sending faster fills the telephony provider's
        # playback buffer, which would let hold music continue after cancellation.
        await asyncio.sleep(len(chunk) / (SAMPLE_RATE * 2))


async def handler(websocket):
    call_sid = None
    monitor_task = None

    async for message in websocket:
        data = json.loads(message)
        event = data.get("event")

        if event == "connected":
            print("WebSocket connected")

        elif event == "start":
            call_sid = data["start"]["call_sid"]
            stream_sid = data["start"].get("stream_sid", call_sid)
            sessions[call_sid] = new_session(stream_sid)
            print(f"[{call_sid}] Call started")

            greeting_audio = await asyncio.to_thread(
                synthesize,
                "मायविकास में आपका स्वागत है। कृपया अपनी समस्या बताइए।",
                "hi",
            )
            await send_pcm(websocket, stream_sid, greeting_audio)
            print(f"[{call_sid}] Greeting played")

            monitor_task = asyncio.create_task(monitor_silence(websocket, call_sid))

        elif event == "media":
            if call_sid and call_sid in sessions:
                payload = base64.b64decode(data["media"]["payload"])
                session = sessions[call_sid]
                session["full_recording"].append(payload)

                # Exotel streams audio continuously, even during silence — so we can't
                # tell "caller stopped talking" from events stopping. Instead, check the
                # actual loudness of each chunk and only reset the timer on real speech.
                samples = np.frombuffer(payload, dtype=np.int16)
                rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2)) if len(samples) else 0
                if rms > SILENCE_RMS_THRESHOLD:
                    session["last_audio_time"] = asyncio.get_event_loop().time()
                    session["has_speech"] = True

                # Discard silence before the caller begins speaking. Once a turn has
                # begun, retain its trailing silence so the monitor can close it cleanly.
                if session["has_speech"]:
                    session["buffer"].append(payload)

                if session["buffer"] and len(session["buffer"]) % 50 == 0:  # don't spam — print every 50 chunks
                    print(f"[{call_sid}] ...receiving audio ({len(session['buffer'])} chunks so far, last RMS={rms:.0f})")

        elif event == "dtmf":
            digit = data["dtmf"]["digit"]
            print(f"[{call_sid}] DTMF pressed: {digit}")
            session = sessions.get(call_sid)
            if session and session["awaiting_dtmf"]:
                chosen_language = DTMF_LANGUAGE_MAP.get(digit)
                if chosen_language:
                    session["language"] = chosen_language
                    session["awaiting_dtmf"] = False
                    print(f"[{call_sid}] Language set via DTMF: {chosen_language}")
                    confirm_audio = await asyncio.to_thread(synthesize, "Language set. Please go ahead.", chosen_language)
                    await send_pcm(websocket, session["stream_sid"], confirm_audio)
                else:
                    print(f"[{call_sid}] Unrecognized digit '{digit}' — not in DTMF_LANGUAGE_MAP")
                    retry_audio = await asyncio.to_thread(
                        synthesize,
                        "Sorry, that wasn't a valid option. Press 1 for Tamil, 2 for Hindi, 3 for English.",
                        "en"
                    )
                    await send_pcm(websocket, session["stream_sid"], retry_audio)

        elif event == "stop":
            session = sessions.get(call_sid)
            if session:
                if session["buffer"] and session["has_speech"]:
                    print(f"[{call_sid}] Call ending with unprocessed audio — flushing final turn...")
                    audio_bytes = b"".join(session["buffer"])
                    session["buffer"] = []
                    session["has_speech"] = False
                    try:
                        await process_turn(websocket, call_sid, audio_bytes)
                    except Exception as e:
                        # Caller's already gone by this point — can't play audio back to them.
                        # Still worth transcribing/logging for your own records, just can't respond.
                        print(f"[{call_sid}] Could not send final response (caller already disconnected): {e}")
                print(f"[{call_sid}] Call ended. Final language={session['language']}, "
                      f"turns={len(session['history'])}")

                # Save the full call's audio to a .wav you can play back and listen to
                if session["full_recording"]:
                    import wave
                    filename = f"call_{call_sid}.wav"
                    with wave.open(filename, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)          # 16-bit
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(b"".join(session["full_recording"]))
                    print(f"[{call_sid}] Saved full call audio to {filename} — open it in any media player")
            if monitor_task:
                monitor_task.cancel()
            sessions.pop(call_sid, None)


async def main():
    print("Server ready on port 5000")
    async with websockets.serve(handler, "0.0.0.0", 5000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
