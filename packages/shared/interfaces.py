"""
Real transcribe() backed by AI4Bharat's IndicConformer (self-hosted, transformers-based).

IMPORTANT LIMITATION: this model needs to be TOLD which language to decode —
it does not auto-detect language on its own. For this first integration test,
TARGET_LANGUAGE is hardcoded below. Real language auto-detection (needed for
the bootstrap logic) is a separate problem to solve later — either by trying
multiple language codes and comparing confidence, or using a small dedicated
language-ID model upstream of this.
"""

import base64
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import wave

import torch
import torchaudio
import numpy as np
from transformers import AutoModel

# One setting drives the STT result, Team B request, and Sarvam reply.
# Supported by the current voice mappings: hi, en, ml, ta.
TARGET_LANGUAGE = os.getenv("MYVIKAS_LANGUAGE", "hi")

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ml": "ml-IN",
    "ta": "ta-IN",
}
SARVAM_SPEAKERS = {
    "en": "ratan",
    "hi": "shubh",
    "ml": "shubh",
    "ta": "ratan",
}


def _load_local_env() -> None:
    """Load simple KEY=VALUE settings from the repository's untracked .env."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()

print("Loading IndicConformer model... (first run downloads weights, can take a few minutes)")
_model = AutoModel.from_pretrained("ai4bharat/indic-conformer-600m-multilingual", trust_remote_code=True)
print("Model loaded.")


def pcm_bytes_to_waveform(pcm_bytes: bytes, source_sample_rate: int) -> torch.Tensor:
    """
    Converts raw 16-bit PCM mono audio bytes (what your telephony server buffers)
    into the 16kHz mono float tensor the model expects.
    """
    audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    wav = torch.from_numpy(audio_np).unsqueeze(0)  # shape: [1, num_samples]

    if source_sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(source_sample_rate, 16000)
        wav = resampler(wav)

    return wav


def transcribe(audio_bytes: bytes) -> dict:
    """
    Real implementation — replaces the stub in packages/shared/interfaces.py.
    Input: raw PCM audio bytes from a call (16-bit, mono, at your call's sample rate).
    Output: {"text": str, "language": str, "confidence": float}
    """
    import time
    start = time.time()

    wav = pcm_bytes_to_waveform(audio_bytes, source_sample_rate=8000)  # match your call's actual rate
    text = _model(wav, TARGET_LANGUAGE, "ctc")

    elapsed = time.time() - start
    print(f"[transcribe] Took {elapsed:.2f}s, result: '{text}'")

    return {
        "text": text,
        "language": TARGET_LANGUAGE,
        "confidence": 0.9,  # placeholder — this model doesn't return a real confidence score directly
    }


def _beep() -> bytes:
    """A reliable audible fallback if cloud TTS is unavailable."""
    sample_rate = 8000
    duration_sec = 0.4
    frequency = 800  # Hz — a clearly audible beep tone

    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    tone = np.sin(2 * np.pi * frequency * t) * 0.5  # 0.5 = volume, keep below 1.0 to avoid clipping
    pcm = (tone * 32767).astype(np.int16)

    return pcm.tobytes()


def _prepare_text_for_tts(text: str) -> str:
    """Remove Markdown and keep responses within Sarvam Bulbul v3's limit."""
    clean_text = re.sub(r"[`*_#]+", "", text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    # A phone caller needs a concise answer. Long RAG answers can take minutes
    # to synthesize and stream, so keep the first response to roughly 40 seconds.
    max_chars = 700
    if len(clean_text) <= max_chars:
        return clean_text

    shortened = clean_text[:max_chars]
    sentence_end = max(shortened.rfind("."), shortened.rfind("!"), shortened.rfind("?"))
    return shortened[:sentence_end + 1] if sentence_end > 0 else shortened


def synthesize(text: str, language: str) -> bytes:
    """
    Generate 8 kHz mono PCM audio through Sarvam Bulbul v3.

    The voice server's ``send_pcm`` function streams raw signed 16-bit PCM, so
    this requests an 8 kHz WAV and returns only its PCM frames.  If Sarvam is
    unavailable, preserve the previous beep response so a live call is still
    demonstrably functional.
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("[tts] SARVAM_API_KEY is not set; using beep fallback")
        return _beep()

    text = _prepare_text_for_tts(text)
    language_code = SARVAM_LANGUAGE_CODES.get(language, "en-IN")
    speaker = SARVAM_SPEAKERS.get(language, "ratan")
    payload = json.dumps(
        {
            "text": text,
            "language_code": language_code,
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.0,
            "speech_sample_rate": 8000,
            "output_audio_codec": "wav",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        SARVAM_TTS_URL,
        data=payload,
        headers={
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)

        wav_bytes = base64.b64decode("".join(result["audios"]))
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            if (
                wav_file.getnchannels() != 1
                or wav_file.getsampwidth() != 2
                or wav_file.getframerate() != 8000
            ):
                raise ValueError(
                    "Sarvam returned unexpected audio format "
                    f"({wav_file.getnchannels()} channel(s), "
                    f"{wav_file.getsampwidth() * 8}-bit, "
                    f"{wav_file.getframerate()} Hz)"
                )
            return wav_file.readframes(wav_file.getnframes())
    except (KeyError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as error:
        print(f"[tts] Sarvam request failed ({error}); using beep fallback")
        return _beep()
