import soundfile as sf

from tts import IndicF5TTS


REFERENCE_AUDIO = (
    "/home/ivang/.cache/huggingface/hub/"
    "models--ai4bharat--IndicF5/"
    "snapshots/ba85abedf18dc479a447eaa0eccbd76ab78a47d5/"
    "prompts/MAR_F_HAPPY_00001.wav"
)

REFERENCE_TEXT = (
    "दिगंतराव्दारे अंतराळ कक्षेतला कचरा "
    "चिन्हित करण्यासाठी प्रयत्न केले जात आहे।"
)

tts = IndicF5TTS()

audio, sample_rate = tts.synthesize(
    text="नमस्ते, यह IndicF5 का परीक्षण है।",
    reference_audio=REFERENCE_AUDIO,
    reference_text=REFERENCE_TEXT,
    speed=0.8,
)

output_path = "/home/ivang/indicf5_api_test.wav"

sf.write(
    output_path,
    audio,
    sample_rate,
)

print(f"Generated: {output_path}")

