import pytest
import asyncio
import os
import json
from core.brain import FridayBrain
from core.tts import FridayTTS
from core.stt import FridaySTT

@pytest.fixture
def brain():
    return FridayBrain()

@pytest.fixture
def tts():
    return FridayTTS()

@pytest.fixture
def stt():
    return FridaySTT()

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
async def test_brain_response(brain):
    response_text = ""
    async for token in brain.get_streaming_response("Hello Friday"):
        response_text += token
    assert isinstance(response_text, str)
    assert len(response_text) > 0
    print(f"Brain Test: {response_text}")

@pytest.mark.asyncio
async def test_tts_generation(tts):
    output_path = "tests/test_output.mp3"
    await tts.generate_speech("Test speech generation", output_path)
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0
    os.remove(output_path)

def test_stt_initialization(stt):
    # Just testing initialization as actual transcription needs audio file
    assert stt.model is not None

def test_registry_loading():
    with open("config/registry.json", "r") as f:
        config = json.load(f)
    assert "ai_logic" in config
    assert "speech" in config
    assert "ui" in config
