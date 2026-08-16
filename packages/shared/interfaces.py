"""
Shared interface between telephony (you) and speech (your friend's Bhashini code).
Swap the stub implementations below for the real Bhashini calls once they're ready —
the function signatures must stay exactly the same so nothing else needs to change.
"""

def transcribe(audio_bytes: bytes) -> dict:
    """
    Input: raw PCM audio bytes (16-bit, mono) captured from the caller.
    Output: {"text": str, "language": str, "confidence": float}

    STUB — replace with a real call to Bhashini's STT API.
    """
    return {
        "text": "I need a birth certificate",
        "language": "en",
        "confidence": 0.95,
    }


def synthesize(text: str, language: str) -> bytes:
    """
    Input: text to speak, target language code.
    Output: raw PCM audio bytes (16-bit, mono) at the call's sample rate.

    STUB — replace with a real call to Bhashini's TTS API.
    For now, returns half a second of silence as a safe placeholder so the
    pipeline runs end to end without crashing on missing audio.
    """
    sample_rate = 8000  # match whatever your Voicebot applet is actually configured to
    duration_sec = 0.5
    num_samples = int(sample_rate * duration_sec)
    return b"\x00\x00" * num_samples
