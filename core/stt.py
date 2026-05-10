import asyncio
from faster_whisper import WhisperModel
import json

class FridaySTT:
    def __init__(self, registry_path="config/registry.json"):
        with open(registry_path, "r") as f:
            self.registry = json.load(f)

        model_size = self.registry["speech"]["whisper_model"].split(".")[0] # e.g. base
        # Run on GPU if available, else CPU
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: str):
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text.strip()

if __name__ == "__main__":
    # Test script would go here
    pass
