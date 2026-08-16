import os

import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

from f5_tts.model import DiT
from f5_tts.infer.utils_infer import load_model, load_vocoder, infer_process


MODEL_REPO = "ai4bharat/IndicF5"


class IndicF5TTS:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"Loading IndicF5 on {self.device}...")

        # Download/cache model files automatically.
        checkpoint_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename="model.safetensors",
        )

        vocab_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename="checkpoints/vocab.txt",
        )

        # Load Vocos.
        self.vocoder = load_vocoder(
            vocoder_name="vocos",
            is_local=False,
            device="cpu",
        )

        # Build F5 architecture.
        self.model = load_model(
            DiT,
            dict(
                dim=1024,
                depth=22,
                heads=16,
                ff_mult=2,
                text_dim=512,
                conv_layers=4,
            ),
            mel_spec_type="vocos",
            vocab_file=vocab_path,
            device="cpu",
        )

        # Load trained checkpoint.
        checkpoint = load_file(
            checkpoint_path,
            device="cpu",
        )

        model_state = {}
        vocoder_state = {}

        for key, value in checkpoint.items():
            key = key.replace("._orig_mod.", ".")

            if key.startswith("ema_model."):
                model_state[key[len("ema_model."):]] = value

            elif key.startswith("vocoder."):
                vocoder_state[key[len("vocoder."):]] = value

        self.model.load_state_dict(
            model_state,
            strict=True,
        )

        self.vocoder.load_state_dict(
            vocoder_state,
            strict=True,
        )

        self.model = self.model.to(self.device)
        self.vocoder = self.vocoder.to(self.device)

        self.model.eval()
        self.vocoder.eval()

        print("IndicF5 loaded successfully.")

    def synthesize(
        self,
        text: str,
        reference_audio: str,
        reference_text: str,
        speed: float = 0.8,
    ):
        audio, sample_rate, _ = infer_process(
            reference_audio,
            reference_text,
            text,
            self.model,
            self.vocoder,
            mel_spec_type="vocos",
            speed=speed,
            device=self.device,
        )

        return audio, sample_rate
