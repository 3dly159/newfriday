import json
import os

REGISTRY_PATH = "config/registry.json"

# Keys injected at runtime purely for the UI to read. They must never be
# persisted back into registry.json (doing so produced "[object Object]" junk).
RUNTIME_ONLY_KEYS = {"system_memory"}


def sanitize_config(config: dict) -> dict:
    """Return a copy of config with runtime-only keys removed."""
    return {k: v for k, v in config.items() if k not in RUNTIME_ONLY_KEYS}


def load_config(path: str = REGISTRY_PATH) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_config(config: dict, path: str = REGISTRY_PATH) -> dict:
    """Persist config to disk after stripping runtime-only keys."""
    clean = sanitize_config(config)
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as f:
        json.dump(clean, f, indent=4)
    return clean
