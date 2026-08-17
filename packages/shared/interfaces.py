"""
Real transcribe() backed by AI4Bharat's IndicConformer (self-hosted, transformers-based).

IMPORTANT LIMITATION: this model needs to be TOLD which language to decode —
it does not auto-detect language on its own. For this first integration test,
TARGET_LANGUAGE is hardcoded below. Real language auto-detection (needed for
the bootstrap logic) is a separate problem to solve later — either by trying
multiple language codes and comparing confidence, or using a small dedicated
language-ID model upstream of this.
"""

import torch
import torchaudio
import numpy as np
from transformers import AutoModel

TARGET_LANGUAGE = "hi"  # change to "ta" for Tamil, etc. — hardcoded for this test

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


def synthesize(text: str, language: str) -> bytes:
    """
    Still a stub — this file only replaces transcribe(). Your friend's TTS work
    (Bhashini or AI4Bharat TTS on Render) fills this in separately.

    Returns an audible beep instead of silence, so you can actually hear when
    a response fires during testing.
    """
    import numpy as np

    sample_rate = 8000
    duration_sec = 0.4
    frequency = 800  # Hz — a clearly audible beep tone

    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    tone = np.sin(2 * np.pi * frequency * t) * 0.5  # 0.5 = volume, keep below 1.0 to avoid clipping
    pcm = (tone * 32767).astype(np.int16)

    return pcm.tobytes()