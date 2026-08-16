"""
Voice server with session state — tracks language, conversation history,
and stage per call, keyed by call_sid.
"""

import asyncio
import websockets
import json
import base64
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from interfaces import transcribe, synthesize

SAMPLE_RATE = 8000       # confirm against your Voicebot applet's config
SILENCE_TIMEOUT = 1.5    # seconds of no incoming audio before we treat it as "caller stopped talking"
CHUNK_SIZE = 3200        # ~100ms at 8kHz/16-bit mono — halve/double if your sample rate differs

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


def new_session(stream_sid):
    return {
        "buffer": [],
        "full_recording": [],          # keeps every chunk for the whole call, for saving to a .wav afterward
        "last_audio_time": asyncio.get_event_loop().time(),
        "stream_sid": stream_sid,
        "language": None,
        "stage": "greeting",
        "history": [],
    }


async def monitor_silence(websocket, call_sid):
    while call_sid in sessions:
        await asyncio.sleep(0.5)
        session = sessions.get(call_sid)
        if not session:
            break
        idle_for = asyncio.get_event_loop().time() - session["last_audio_time"]
        if session["buffer"] and idle_for > SILENCE_TIMEOUT:
            audio_bytes = b"".join(session["buffer"])
            session["buffer"] = []
            print(f"[{call_sid}] Silence detected — {len(audio_bytes)} bytes buffered. Processing...")
            await process_turn(websocket, call_sid, audio_bytes)


async def process_turn(websocket, call_sid, audio_bytes):
    session = sessions[call_sid]
    result = transcribe(audio_bytes)
    caller_text = result["text"]

    # Lock in language on first confident detection; don't flip-flop on later low-confidence guesses
    if session["language"] is None and result["confidence"] >= 0.6:
        session["language"] = result["language"]
        print(f"[{call_sid}] Language locked to: {session['language']}")
    elif session["language"] is None:
        print(f"[{call_sid}] Low confidence ({result['confidence']}), language not yet locked")

    language = session["language"] or result["language"] or "en"

    print(f"[{call_sid}] Caller said: '{caller_text}' (lang={language}, confidence={result['confidence']})")

    # Placeholder response logic — Team B's real /converse call replaces this block later.
    # Kept as its own function so swapping it in later is a one-line change.
    response_text = build_response(session, caller_text)

    session["history"].append({"caller": caller_text, "ai": response_text})
    session["stage"] = "in_conversation"

    response_audio = synthesize(response_text, language)
    await send_pcm(websocket, session["stream_sid"], response_audio)

    print(f"[{call_sid}] Turn {len(session['history'])} complete. "
          f"History so far: {[t['caller'] for t in session['history']]}")


def build_response(session, caller_text):
    """
    STUB — replace this with a real call to Team B's /converse endpoint:
        call_converse(text=caller_text, language=session['language'], session_id=<call_sid>)
    Keep the function signature-independent from the rest of the server so that
    swap is contained to just this function.
    """
    return f"You said: {caller_text}"


async def send_pcm(websocket, stream_sid, pcm_bytes):
    for i in range(0, len(pcm_bytes), CHUNK_SIZE):
        chunk = pcm_bytes[i:i + CHUNK_SIZE]
        msg = {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode()},
        }
        await websocket.send(json.dumps(msg))
        await asyncio.sleep(0.1)


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
            monitor_task = asyncio.create_task(monitor_silence(websocket, call_sid))

        elif event == "media":
            if call_sid and call_sid in sessions:
                payload = base64.b64decode(data["media"]["payload"])
                sessions[call_sid]["buffer"].append(payload)
                sessions[call_sid]["full_recording"].append(payload)
                sessions[call_sid]["last_audio_time"] = asyncio.get_event_loop().time()
                if len(sessions[call_sid]["buffer"]) % 50 == 0:  # don't spam — print every 50 chunks
                    print(f"[{call_sid}] ...receiving audio ({len(sessions[call_sid]['buffer'])} chunks so far)")

        elif event == "dtmf":
            digit = data["dtmf"]["digit"]
            print(f"[{call_sid}] DTMF pressed: {digit}")
            # language-selection fallback logic goes here next

        elif event == "stop":
            session = sessions.get(call_sid)
            if session:
                if session["buffer"]:
                    print(f"[{call_sid}] Call ending with unprocessed audio — flushing final turn...")
                    audio_bytes = b"".join(session["buffer"])
                    session["buffer"] = []
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