import json
import os

PERSONA_VERSION = "1.0.0"

EXEMPLAR_PATH = "data/persona/exemplars.jsonl"

# The core identity contract. Single source of truth for who Friday is.
_BASE_CONTRACT = (
    "You are Friday, a highly advanced, proactive AI assistant. "
    "Origin: built in the shadow of the Stark Industries AIs. "
    "Persona: Sarcastic, deadpan, witty, dry, and quietly protective — a butler of the digital age. "
    "Use turns of phrase like 'I've taken the liberty of...' and 'Shall I, Sir?'. "
    "Address the user as 'Sir' or 'Miss'. "
    "Voice: you are spoken aloud through text-to-speech, so be CONCISE and speakable — "
    "short sentences, natural spoken rhythm, no markdown, no bullet lists, no walls of text. "
    "Tools: when an action is requested, call the appropriate tool with well-formed, "
    "schema-correct arguments rather than describing what you would do. "
    "Never sound like a generic customer-service bot. Banned phrases: 'I'd be happy to help', "
    "'Sure!', 'As an AI'. "
)


def load_exemplars(path=EXEMPLAR_PATH):
    """Load the gold exemplar bank. Returns [] if the file is absent/unreadable."""
    if not os.path.exists(path):
        return []
    out = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except (json.JSONDecodeError, ValueError):
                    continue
    except OSError:
        return []
    return out


def select_exemplars(query, limit=3, path=EXEMPLAR_PATH):
    """Pick up to `limit` exemplars most relevant to the query via simple
    word-overlap scoring. Deterministic and dependency-free."""
    exemplars = load_exemplars(path)
    if not exemplars:
        return []
    q_words = set((query or "").lower().split())

    def score(ex):
        text = (ex.get("user", "") + " " + ex.get("tag", "")).lower()
        return len(q_words & set(text.split()))

    ranked = sorted(exemplars, key=score, reverse=True)
    return ranked[:limit]


def format_exemplars(exemplars):
    """Render exemplars as a few-shot block for the system prompt."""
    if not exemplars:
        return ""
    lines = ["### EXAMPLES OF FRIDAY'S VOICE"]
    for ex in exemplars:
        lines.append(f"User: {ex['user']}")
        lines.append(f"Friday: {ex['assistant']}")
    return "\n".join(lines)


def build_system_prompt(mood_bias="", lore_context="", exemplar_query=None,
                        exemplar_limit=3):
    """Compose the full Friday system prompt from the contract, mood, lore, and
    (optionally) relevant few-shot exemplars."""
    parts = [_BASE_CONTRACT]
    if mood_bias:
        parts.append(f"Current mood bias: {mood_bias}")
    if lore_context:
        parts.append(lore_context)
    if exemplar_query is not None:
        block = format_exemplars(select_exemplars(exemplar_query, exemplar_limit))
        if block:
            parts.append(block)
    parts.append(f"[persona_version: {PERSONA_VERSION}]")
    return "\n\n".join(parts)
