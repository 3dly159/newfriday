import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

REGISTRY_PATH = "config/registry.json"

# Keys injected at runtime purely for the UI to read. They must never be
# persisted back into registry.json (doing so produced "[object Object]" junk).
RUNTIME_ONLY_KEYS = {"system_memory"}


# --- Schema (improvement plan #5) -------------------------------------------
# Each section forbids nothing extra (extra="allow") for forward-compat, but
# enforces the types/ranges/enums of the fields we actually rely on.

class AILogic(BaseModel):
    model_config = ConfigDict(extra="allow")
    model_provider: str = Field(pattern="^(ollama|anthropic|openai)$")
    llm_model: str = Field(min_length=1)
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0, le=32768)
    base_url: Optional[str] = None


class Speech(BaseModel):
    model_config = ConfigDict(extra="allow")
    tts_voice: str = Field(min_length=1)
    speech_rate: str
    vad_threshold: int = Field(ge=0)
    whisper_model: str = Field(min_length=1)
    interaction_mode: str = Field(pattern="^(continuous|wake_word)$")


class UI(BaseModel):
    model_config = ConfigDict(extra="allow")
    orb_glow_intensity: float = Field(ge=0.0)
    hud_transparency: float = Field(ge=0.0, le=1.0)
    theme_color: str


class System(BaseModel):
    model_config = ConfigDict(extra="allow")
    proactive_interval: int = Field(gt=0)
    # Stored as strings ("true"/"false") by the existing UI; accept str or bool.
    auto_approve_hid: object = None
    capture_dataset: object = None


class RegistrySchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    ai_logic: AILogic
    speech: Speech
    ui: UI
    system: System


def sanitize_config(config: dict) -> dict:
    """Return a copy of config with runtime-only keys removed."""
    return {k: v for k, v in config.items() if k not in RUNTIME_ONLY_KEYS}


def validate_config(config: dict):
    """Validate an incoming config against RegistrySchema.

    Returns (ok: bool, errors: list[str], cleaned: dict). `cleaned` has the
    runtime-only keys stripped; on success it is the validated, dumped config.
    """
    cleaned = sanitize_config(config)
    try:
        model = RegistrySchema.model_validate(cleaned)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return False, errors, cleaned
    # model_dump round-trips known fields + preserves extras; merge over cleaned
    # so we never drop forward-compat keys the schema didn't name.
    dumped = model.model_dump()
    merged = {**cleaned, **dumped}
    return True, [], merged


def load_config(path: str = REGISTRY_PATH) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_config(config: dict, path: str = REGISTRY_PATH) -> dict:
    """Persist config to disk after stripping runtime-only keys."""
    clean = sanitize_config(config)
    from core.atomicio import atomic_write_json
    atomic_write_json(path, clean)
    return clean
