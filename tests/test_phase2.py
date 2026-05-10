import pytest
from core.personality import FridayPersonality

def test_personality_content():
    personality = FridayPersonality()
    prompt = personality.get_system_prompt()
    assert "Sarcastic" in prompt
    assert "butler" in prompt.lower()
    assert "concise" in prompt.lower()

def test_recency_cue():
    personality = FridayPersonality()
    cue = personality.get_recency_cue("Test context")
    assert "Test context" in cue
    assert "[VOICE CUE" in cue

def test_tonal_checkpoint():
    personality = FridayPersonality()
    checkpoint = personality.get_tonal_checkpoint()
    assert "Tonal Checkpoint" in checkpoint
