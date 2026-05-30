"""Milestone 1 (voice reliability) unit tests.

These cover the pure, deterministic logic added in this milestone so it can be
verified without a live microphone, LLM, or network.
"""
import json

from core.stt import is_hallucination, filter_transcription
from core.proactive import extract_json
from core.config import sanitize_config, save_config
from core.agents import LegionBroker


# --- STT hallucination gating -------------------------------------------------

def test_silence_phrases_are_dropped():
    assert is_hallucination("Thank you.")
    assert is_hallucination(" you ")
    assert is_hallucination("")
    assert is_hallucination("...")


def test_real_speech_is_kept():
    assert not is_hallucination("Friday, what's the weather today?")
    assert not is_hallucination("Open my email please")


def test_no_speech_prob_gate():
    assert is_hallucination("hello there", no_speech_prob=0.9)
    assert not is_hallucination("hello there", no_speech_prob=0.1)


def test_short_low_confidence_dropped():
    assert is_hallucination("hm", avg_logprob=-2.0)
    assert not is_hallucination("hm", avg_logprob=-0.1)


def test_filter_joins_real_segments_and_drops_noise():
    segs = [
        ("Hey Friday.", 0.1, -0.3),
        ("you", 0.95, -0.5),          # silence hallucination
        ("How are you?", 0.1, -0.2),
    ]
    out = filter_transcription(segs)
    assert "Hey Friday." in out
    assert "How are you?" in out


def test_filter_all_noise_returns_empty():
    segs = [("you", 0.95, -0.5), ("Thank you.", 0.9, -0.4)]
    assert filter_transcription(segs) == ""


# --- Proactive tolerant JSON parsing -----------------------------------------

def test_extract_plain_json():
    assert extract_json('{"decision": "SPEAK"}')["decision"] == "SPEAK"


def test_extract_fenced_json():
    text = 'Sure!\n```json\n{"decision": "ACT", "payload": "x"}\n```\nDone'
    assert extract_json(text)["payload"] == "x"


def test_extract_prose_wrapped_json():
    text = 'I think {"decision": "SILENCE"} is best here.'
    assert extract_json(text)["decision"] == "SILENCE"


def test_extract_garbage_returns_none():
    assert extract_json("no json here") is None
    assert extract_json("") is None
    assert extract_json("{not valid json}") is None
    assert extract_json(None) is None


# --- Config sanitization ------------------------------------------------------

def test_sanitize_removes_runtime_keys():
    cfg = {"ai_logic": {"x": 1}, "system_memory": {"bio": {}}}
    clean = sanitize_config(cfg)
    assert "system_memory" not in clean
    assert clean["ai_logic"]["x"] == 1


def test_save_config_strips_runtime_keys(tmp_path):
    path = tmp_path / "registry.json"
    save_config({"ai_logic": {"x": 1}, "system_memory": {"a": 1}}, str(path))
    saved = json.loads(path.read_text())
    assert "system_memory" not in saved
    assert saved["ai_logic"]["x"] == 1


# --- Legion provider-agnostic construction -----------------------------------

class _FakeBrain:
    provider = "ollama"
    client = object()  # sentinel; truthy so agents don't build an Anthropic client
    config = {"ai_logic": {"llm_model": "test-model"}}


def test_legion_inherits_brain_provider():
    broker = LegionBroker(_FakeBrain())
    scout = broker.agents["scout"]
    assert scout.provider == "ollama"
    assert scout.model == "test-model"
    assert scout.client is _FakeBrain.client
