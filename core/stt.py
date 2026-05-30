import json
from faster_whisper import WhisperModel

# Phrases Whisper commonly hallucinates on silence, breaths, or background noise.
# Compared after normalization (lowercased, surrounding punctuation stripped).
HALLUCINATION_PHRASES = {
    "you", "thank you", "thanks", "thanks for watching",
    "thank you for watching", "please subscribe", "like and subscribe",
    "bye", "okay", "ok", "uh", "um", "so", "the", "yeah",
    "i'm sorry", "thanks for listening",
    "subtitles by the amara.org community", "amara.org",
    "transcription by castingwords",
}

# faster-whisper confidence gates. A segment whose probability of being
# non-speech exceeds this is almost certainly silence.
NO_SPEECH_THRESHOLD = 0.6
# Very short segments below this average log-probability are treated as noise.
LOGPROB_THRESHOLD = -1.0


def _normalize(text: str) -> str:
    """Lowercase and strip surrounding whitespace/punctuation for comparison."""
    return text.strip().lower().strip(".!?,… \t\n").strip()


def is_hallucination(text: str, no_speech_prob: float = 0.0, avg_logprob: float = 0.0) -> bool:
    """Return True if a transcription segment should be discarded as noise."""
    norm = _normalize(text)
    if not norm:
        return True
    if no_speech_prob >= NO_SPEECH_THRESHOLD:
        return True
    if norm in HALLUCINATION_PHRASES:
        return True
    # Very short *and* low-confidence is almost always a hallucination.
    if len(norm) <= 3 and avg_logprob <= LOGPROB_THRESHOLD:
        return True
    return False


def filter_transcription(segments) -> str:
    """Filter and join Whisper segments.

    Args:
        segments: iterable of (text, no_speech_prob, avg_logprob) tuples.

    Returns:
        Cleaned transcription string, or "" if everything was noise.
    """
    kept = []
    for text, no_speech_prob, avg_logprob in segments:
        if not is_hallucination(text, no_speech_prob, avg_logprob):
            kept.append(text.strip())

    combined = " ".join(kept).strip()
    # A final whole-utterance check catches single-phrase hallucinations
    # that individually passed the per-segment confidence gates.
    if is_hallucination(combined):
        return ""
    return combined


class FridaySTT:
    def __init__(self, registry_path="config/registry.json"):
        with open(registry_path, "r") as f:
            self.registry = json.load(f)

        # Honor the configured model name directly (e.g. "base.en"). The
        # English-only models are noticeably more accurate for English speech.
        model_size = self.registry["speech"]["whisper_model"]
        # Run on CPU with int8 for portability; swap to GPU where available.
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: str) -> str:
        # vad_filter uses Silero VAD to drop non-speech audio before decoding,
        # which is the first and strongest line of defense against silence
        # hallucinations.
        segments, info = self.model.transcribe(
            audio_path, beam_size=5, vad_filter=True
        )
        seg_tuples = [
            (
                seg.text,
                getattr(seg, "no_speech_prob", 0.0),
                getattr(seg, "avg_logprob", 0.0),
            )
            for seg in segments
        ]
        return filter_transcription(seg_tuples)


if __name__ == "__main__":
    pass
