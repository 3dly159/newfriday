import json
import os
from datetime import datetime


class DatasetCapturer:
    """Appends finalized Friday exchanges to a JSONL file in chat format for
    later fine-tuning. Opt-in and local-only; never transmits anything."""

    def __init__(self, enabled=False, path="data/dataset/friday_sft.jsonl",
                 persona_version="unknown"):
        self.enabled = enabled
        self.path = path
        self.persona_version = persona_version

    def capture(self, system, user, reply, model, tool_calls=None):
        """Write one training record. No-op if disabled or reply is empty.
        Never raises — capture must not break the voice loop."""
        if not self.enabled:
            return
        if not reply or not reply.strip():
            return
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": reply},
        ]
        record = {
            "messages": messages,
            "meta": {
                "persona_version": self.persona_version,
                "model": model,
                "ts": datetime.now().isoformat(),
            },
        }
        if tool_calls:
            record["meta"]["tool_calls"] = tool_calls
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except (OSError, TypeError) as e:
            print(f"[Dataset] capture skipped: {e}")
