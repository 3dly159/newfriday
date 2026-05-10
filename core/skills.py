import json
import os
import logging

logger = logging.getLogger("Friday.Clawhub")

class ClawhubManager:
    def __init__(self, memory):
        self.memory = memory
        self.hub_path = "config/clawhub.json"
        self.skills_path = "config/skills.json"
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(self.hub_path):
            with open(self.hub_path, "w") as f:
                json.dump({"available_skills": []}, f)
        if not os.path.exists(self.skills_path):
            with open(self.skills_path, "w") as f:
                json.dump({"installed_skills": []}, f)

    def load_manifest(self, remote_url=None):
        if remote_url:
            try:
                import httpx
                response = httpx.get(remote_url)
                return response.json()
            except Exception as e:
                logger.error(f"Failed to fetch remote Clawhub: {e}")
                return {"available_skills": []}

        with open(self.hub_path, "r") as f:
            return json.load(f)

    def install_skill(self, skill_id: str, remote_url=None):
        manifest = self.load_manifest(remote_url)
        skill = next((s for s in manifest["available_skills"] if s["id"] == skill_id), None)

        if not skill:
            return f"Skill {skill_id} not found in Clawhub."

        with open(self.skills_path, "r") as f:
            skills = json.load(f)

        if any(s["id"] == skill_id for s in skills["installed_skills"]):
            return f"Skill {skill_id} is already installed."

        skills["installed_skills"].append(skill)
        with open(self.skills_path, "w") as f:
            json.dump(skills, f, indent=4)

        # Update Memory Layer 3 (Skill)
        self.memory.layers["skill"][skill_id] = skill
        self.memory.save()

        return f"Successfully installed skill: {skill['name']}"

    def persist_script_as_skill(self, name: str, description: str, code: str, language: str):
        """Allows Friday to save a successful script as a permanent skill."""
        skill_id = f"custom_{name.lower().replace(' ', '_')}"
        skill = {
            "id": skill_id,
            "name": name,
            "description": description,
            "code": code,
            "language": language,
            "type": "custom"
        }

        with open(self.skills_path, "r") as f:
            skills = json.load(f)

        skills["installed_skills"].append(skill)
        with open(self.skills_path, "w") as f:
            json.dump(skills, f, indent=4)

        self.memory.layers["skill"][skill_id] = skill
        self.memory.save()

        return f"Persisted custom skill: {name}"

    def get_installed_skills_prompt(self):
        """Returns a string describing installed skills for the system prompt."""
        with open(self.skills_path, "r") as f:
            skills = json.load(f)

        if not skills["installed_skills"]:
            return "No custom skills installed."

        prompt = "### INSTALLED CUSTOM SKILLS\n"
        for s in skills["installed_skills"]:
            prompt += f"- {s['name']} ({s['id']}): {s['description']}\n"
        return prompt
