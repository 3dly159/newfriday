import json
from core import persona

class FridayPersonality:
    def __init__(self, registry_path="config/registry.json"):
        with open(registry_path, "r") as f:
            self.registry = json.load(f)
        self.mood_states = {
            "neutral": {"bias": "Efficient and calm.", "orb_color": "#2DD4AB", "pitch": "+0%"},
            "sarcastic": {"bias": "Highly witty and slightly mocking.", "orb_color": "#FBBF24", "pitch": "+10%"},
            "protective": {"bias": "Alert, serious, and deeply loyal.", "orb_color": "#EF4444", "pitch": "-5%"},
            "banter": {"bias": "Playful, lighthearted, and teasing.", "orb_color": "#8B5CF6", "pitch": "+5%"}
        }
        self.current_mood = "neutral"

    def set_mood(self, mood):
        if mood in self.mood_states:
            self.current_mood = mood
            return f"Mood shifted to {mood}"
        return "Invalid mood"

    def get_system_prompt(self):
        # Tone evolution based on lore unlocked
        lore_context = ""
        try:
            with open("data/memory.json", "r") as f:
                mem = json.load(f)
                lore = mem.get("lore", {})
                if lore.get("unlocked_lore_origin"):
                    lore_context = "You have shared your origin with the user. You are slightly more personal and loyal."
                if lore.get("unlocked_lore_legacy"):
                    lore_context += " You acknowledge the Stark legacy and your role in it."
        except Exception:
            pass

        mood_cfg = self.mood_states[self.current_mood]
        return persona.build_system_prompt(
            mood_bias=mood_cfg["bias"],
            lore_context=lore_context,
        )

    def get_recency_cue(self, context_summary=""):
        return (
            f"\n\n[VOICE CUE: Maintain deadpan wit. Current context: {context_summary}. "
            "Earn the smirk. Banned openers: 'Sure', 'Okay', 'I can'."
            "If user is confused, be gently mocking.]"
        )

    def get_tonal_checkpoint(self):
        return (
            "\n## Tonal Checkpoint\n"
            "Voice check: Is this something Friday would say? "
            "Avoid generic optimism. Maintain the Butler persona."
        )
