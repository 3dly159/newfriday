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
async def test_brain_response(brain):
    response = await brain.get_response("Hello Friday")
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"Brain Test: {response}")

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
