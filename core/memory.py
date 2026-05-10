import json
import os
from datetime import datetime

class FridayMemory:
    """Implementation of the 7-Layer Cognitive Memory Architecture."""

    def __init__(self, storage_path="data/memory.json"):
        self.storage_path = storage_path
        self.layers = {
            "bio": {},          # Layer 1: Persistent user facts (Name, preferences)
            "lore": {},         # Layer 2: Project Friday backstory & ARG state
            "skill": {},        # Layer 3: Learned tools & clawhub manifests
            "script": [],       # Layer 4: History of executed scripts & outcomes
            "social": {         # Layer 5: Relationship metrics (Trust, Tone)
                "trust_level": 1.0,
                "banter_score": 0.5
            },
            "task": [],         # Layer 6: Current goals & proactive queue
            "episodic": []      # Layer 7: Recent session context (Last 20 exchanges)
        }
        self.load()

    def load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                self.layers.update(json.load(f))

    def save(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.layers, f, indent=4)

    def add_episodic(self, role, content):
        self.layers["episodic"].append({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        })
        # Keep last 20
        if len(self.layers["episodic"]) > 20:
            self.layers["episodic"].pop(0)
        self.save()

    def update_bio(self, key, value):
        self.layers["bio"][key] = value
        self.save()

    def get_context_string(self):
        """Compiles relevant memory into a context string for the LLM."""
        context = "### COGNITIVE CONTEXT\n"
        context += f"USER_BIO: {json.dumps(self.layers['bio'])}\n"
        context += f"CURRENT_TASKS: {json.dumps(self.layers['task'])}\n"
        context += f"RELATIONSHIP: {json.dumps(self.layers['social'])}\n"
        return context

    def add_task(self, task_name, description):
        self.layers["task"].append({
            "id": len(self.layers["task"]),
            "name": task_name,
            "desc": description,
            "status": "pending"
        })
        self.save()
