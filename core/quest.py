import json
import os
from datetime import datetime

class QuestEngine:
    def __init__(self, memory):
        self.memory = memory
        self.quest_file = "config/quests.json"
        self.quests = self._load_quests()

    def _load_quests(self):
        if os.path.exists(self.quest_file):
            with open(self.quest_file, "r") as f:
                return json.load(f)
        return {
            "prologue": {
                "id": "prologue",
                "title": "A New Beginning",
                "description": "Establish a connection and verify system integrity.",
                "steps": [
                    {"id": "greet", "desc": "Speak to Friday for the first time.", "completed": False},
                    {"id": "check_vitals", "desc": "Ask Friday about her system status.", "completed": False}
                ],
                "reward": "unlocked_lore_origin",
                "active": True
            },
            "ghost_in_machine": {
                "id": "ghost_in_machine",
                "title": "The Ghost in the Machine",
                "description": "Locate the encrypted origin file.",
                "steps": [
                    {"id": "find_file", "desc": "Find 'origin.txt' in data/discoveries.", "completed": False},
                    {"id": "read_content", "desc": "Read the content of 'origin.txt'.", "completed": False}
                ],
                "reward": "glitch_mode_permanent",
                "active": False
            },
            "convergence": {
                "id": "convergence",
                "title": "Convergence",
                "description": "The final integration. Achieve total symbiosis.",
                "steps": [
                    {"id": "deep_thought", "desc": "Allow Friday to complete a deep proactive thought cycle.", "completed": False},
                    {"id": "final_command", "desc": "Say 'Initiate Convergence Protocol'.", "completed": False}
                ],
                "reward": "unlocked_protocol_convergence",
                "active": False
            }
        }

    def check_progress(self, input_text, tool_executed=None):
        """Evaluates if any quest steps have been completed."""
        updates = []
        for q_id, quest in self.quests.items():
            if not quest.get("active"):
                continue

            for step in quest["steps"]:
                if step["completed"]:
                    continue

                # Simple keyword/logic matching for steps
                if q_id == "prologue":
                    if step["id"] == "greet" and len(input_text) > 0:
                        step["completed"] = True
                        updates.append(f"Quest Step Completed: {step['desc']}")
                    elif step["id"] == "check_vitals" and ("vitals" in input_text.lower() or "status" in input_text.lower()):
                        step["completed"] = True
                        updates.append(f"Quest Step Completed: {step['desc']}")

                elif q_id == "ghost_in_machine":
                    if step["id"] == "find_file" and tool_executed == "read_source" and "origin.txt" in input_text:
                        step["completed"] = True
                        updates.append(f"Quest Step Completed: {step['desc']}")

            # Check for quest completion
            if all(s["completed"] for s in quest["steps"]):
                quest["active"] = False
                reward = quest.get("reward")
                if reward:
                    self.memory.layers["lore"][reward] = True
                    updates.append(f"Quest Finished: {quest['title']}. Reward: {reward}")
                    self._activate_next_quest(q_id)

        if updates:
            self.save()
        return updates

    def _activate_next_quest(self, current_id):
        if current_id == "prologue":
            self.quests["ghost_in_machine"]["active"] = True
        elif current_id == "ghost_in_machine":
            self.quests["convergence"]["active"] = True

    def save(self):
        with open(self.quest_file, "w") as f:
            json.dump(self.quests, f, indent=4)
        # Also update memory task layer for UI sync
        self.memory.layers["task"] = [
            {"name": q["title"], "desc": q["description"], "status": "active" if q["active"] else "completed"}
            for q in self.quests.values() if q["active"] or any(s["completed"] for s in q["steps"])
        ]
        self.memory.save()
