import asyncio
import edge_tts
import json
import os

TICKS_PER_MS = 10000  # Edge-TTS reports offset/duration in 100-nanosecond ticks


def boundary_to_word(chunk):
    """Convert one Edge-TTS WordBoundary chunk to our word-timing dict."""
    return {
        "word": chunk["text"],
        "offset_ms": chunk["offset"] // TICKS_PER_MS,
        "duration_ms": chunk["duration"] // TICKS_PER_MS,
    }


def words_from_chunks(chunks):
    """Filter an Edge-TTS chunk stream down to word-timing dicts."""
    return [boundary_to_word(c) for c in chunks if c.get("type") == "WordBoundary"]


class FridayTTS:
    def __init__(self, registry_path="config/registry.json"):
        with open(registry_path, "r") as f:
            self.registry = json.load(f)

        self.voice = self.registry["speech"]["tts_voice"]
        self.rate = self.registry["speech"]["speech_rate"]

    async def generate_speech(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(output_path)
        return output_path

    async def generate_speech_timed(self, text: str, output_path: str):
        """Synthesize speech and return (output_path, words) where words is a list
        of {word, offset_ms, duration_ms} from Edge-TTS WordBoundary events."""
        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, boundary="WordBoundary")
        audio = bytearray()
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
            else:
                chunks.append(chunk)
        with open(output_path, "wb") as f:
            f.write(audio)
        return output_path, words_from_chunks(chunks)

if __name__ == "__main__":
    # Quick test
    tts = FridayTTS()
    asyncio.run(tts.generate_speech("Hello, I am Friday.", "test_speech.mp3"))
