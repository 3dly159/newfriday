"""Tests for /api/config schema validation (improvement plan #5)."""
import json
from core.config import validate_config, sanitize_config, save_config


def _good():
    return {
        "ai_logic": {"model_provider": "ollama", "llm_model": "x",
                     "temperature": 0.7, "max_tokens": 1024,
                     "base_url": "http://localhost:11434/v1"},
        "speech": {"tts_voice": "en-GB-SoniaNeural", "speech_rate": "+0%",
                   "vad_threshold": 800, "whisper_model": "base.en",
                   "interaction_mode": "continuous"},
        "ui": {"orb_glow_intensity": 1, "hud_transparency": 0.15, "theme_color": "#2DD4AB"},
        "system": {"proactive_interval": 20, "auto_approve_hid": "false",
                   "capture_dataset": "false"},
    }


def test_good_config_passes():
    ok, errors, cleaned = validate_config(_good())
    assert ok is True
    assert errors == []
    assert cleaned["ai_logic"]["model_provider"] == "ollama"


def test_runtime_only_keys_are_stripped_before_validation():
    cfg = _good()
    cfg["system_memory"] = {"bio": {}}  # injected UI blob, must not persist
    ok, errors, cleaned = validate_config(cfg)
    assert ok is True
    assert "system_memory" not in cleaned


def test_bad_provider_rejected():
    cfg = _good()
    cfg["ai_logic"]["model_provider"] = "skynet"
    ok, errors, cleaned = validate_config(cfg)
    assert ok is False
    assert any("model_provider" in e for e in errors)


def test_bad_interaction_mode_rejected():
    cfg = _good()
    cfg["speech"]["interaction_mode"] = "telepathy"
    ok, errors, cleaned = validate_config(cfg)
    assert ok is False
    assert any("interaction_mode" in e for e in errors)


def test_non_numeric_temperature_rejected():
    cfg = _good()
    cfg["ai_logic"]["temperature"] = "object Object"
    ok, errors, cleaned = validate_config(cfg)
    assert ok is False
    assert any("temperature" in e for e in errors)


def test_temperature_out_of_range_rejected():
    cfg = _good()
    cfg["ai_logic"]["temperature"] = 9.0
    ok, errors, cleaned = validate_config(cfg)
    assert ok is False
    assert any("temperature" in e for e in errors)


def test_section_must_be_object():
    cfg = _good()
    cfg["ui"] = "[object Object]"  # the exact corruption we saw before
    ok, errors, cleaned = validate_config(cfg)
    assert ok is False
    assert any("ui" in e for e in errors)


def test_unknown_extra_field_allowed():
    # Forward-compatibility: unknown keys inside a section don't break validation.
    cfg = _good()
    cfg["ui"]["future_knob"] = 5
    ok, errors, cleaned = validate_config(cfg)
    assert ok is True
    assert cleaned["ui"]["future_knob"] == 5


def test_save_config_still_strips_runtime_keys(tmp_path):
    path = tmp_path / "r.json"
    save_config({"ai_logic": {"model_provider": "ollama"}, "system_memory": {"a": 1}}, str(path))
    saved = json.loads(path.read_text())
    assert "system_memory" not in saved
