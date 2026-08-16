import os
import tempfile

import soundfile as sf
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse

from .tts import IndicF5TTS


app = FastAPI(title="IndicF5 TTS Service")

print("Loading IndicF5...")
tts = IndicF5TTS()
print("IndicF5 ready.")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "IndicF5 TTS",
    }


@app.post("/tts")
async def synthesize(
    text: str = Form(...),
    reference_text: str = Form(...),
    reference_audio: UploadFile = File(...),
    speed: float = Form(0.8),
):
    suffix = os.path.splitext(reference_audio.filename or ".wav")[1]

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp:
        temp.write(await reference_audio.read())
        reference_audio_path = temp.name

    try:
        audio, sample_rate = tts.synthesize(
            text=text,
            reference_audio=reference_audio_path,
            reference_text=reference_text,
            speed=speed,
        )

        output_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
        ).name

        sf.write(output_path, audio, sample_rate)

        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename="generated.wav",
        )

    finally:
        if os.path.exists(reference_audio_path):
            os.remove(reference_audio_path)
