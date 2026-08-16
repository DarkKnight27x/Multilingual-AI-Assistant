"""
Your own voice server — built on what you learned from the echobot repo,
but instead of echoing audio blindly, it buffers the caller's speech,
waits for a pause, then hands that audio to transcribe()/synthesize().

Run this INSTEAD of simple_server.py (stop that one first — same port).
"""

import asyncio
import websockets
import json
import base64
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from interfaces import transcribe, synthesize

SAMPLE_RATE = 8000       # confirm against your Voicebot applet's config — change to 16000 if that's what it shows
SILENCE_TIMEOUT = 1.5    # seconds of no incoming audio before we treat it as "caller stopped talking"
CHUNK_SIZE = 3200        # ~100ms at 8kHz/16-bit mono — halve/double if your sample rate differs

sessions = {}  # call_sid -> {"buffer": [...], "last_audio_time": float}


async def monitor_silence(websocket, call_sid, stream_sid):
    """Runs alongside the call, watching for a pause in incoming audio."""
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
            await process_turn(websocket, call_sid, stream_sid, audio_bytes)


async def process_turn(websocket, call_sid, stream_sid, audio_bytes):
    """One full turn: transcribe what was said, decide a response, speak it back."""
    result = transcribe(audio_bytes)
    print(f"[{call_sid}] Caller said: '{result['text']}' "
          f"(lang={result['language']}, confidence={result['confidence']})")

    # Placeholder response logic — Team B's real /converse endpoint replaces this line later
    response_text = f"You said: {result['text']}"

    response_audio = synthesize(response_text, result["language"])
    await send_pcm(websocket, stream_sid, response_audio)
    print(f"[{call_sid}] Response sent.")


async def send_pcm(websocket, stream_sid, pcm_bytes):
    """Send audio back to the caller in paced chunks, per Exotel's protocol rules."""
    for i in range(0, len(pcm_bytes), CHUNK_SIZE):
        chunk = pcm_bytes[i:i + CHUNK_SIZE]
        msg = {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode()},
        }
        await websocket.send(json.dumps(msg))
        await asyncio.sleep(0.1)  # pace roughly in real time — don't dump it all at once


async def handler(websocket):
    call_sid = None
    stream_sid = None
    monitor_task = None

    async for message in websocket:
        data = json.loads(message)
        event = data.get("event")

        if event == "connected":
            print("WebSocket connected")

        elif event == "start":
            call_sid = data["start"]["call_sid"]
            stream_sid = data["start"].get("stream_sid", call_sid)
            sessions[call_sid] = {
                "buffer": [],
                "last_audio_time": asyncio.get_event_loop().time(),
            }
            print(f"[{call_sid}] Call started")
            monitor_task = asyncio.create_task(monitor_silence(websocket, call_sid, stream_sid))

        elif event == "media":
            if call_sid and call_sid in sessions:
                payload = base64.b64decode(data["media"]["payload"])
                sessions[call_sid]["buffer"].append(payload)
                sessions[call_sid]["last_audio_time"] = asyncio.get_event_loop().time()

        elif event == "dtmf":
            digit = data["dtmf"]["digit"]
            print(f"[{call_sid}] DTMF pressed: {digit}")
            # language-selection fallback logic goes here later

        elif event == "stop":
            print(f"[{call_sid}] Call ended")
            if monitor_task:
                monitor_task.cancel()
            sessions.pop(call_sid, None)


async def main():
    print("Server ready on port 5000")
    async with websockets.serve(handler, "0.0.0.0", 5000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
