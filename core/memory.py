import json
import os
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

class FridayMemory:
    """Implementation of the 7-Layer Cognitive Memory Architecture."""

    def __init__(self, storage_path="data/memory.json", vector_db_path="data/vector_db"):
        self.storage_path = storage_path
        self.vector_db_path = vector_db_path
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

        # Initialize ChromaDB for Semantic Memory
        self.chroma_client = chromadb.PersistentClient(path=self.vector_db_path)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.chroma_client.get_or_create_collection(
            name="friday_semantic_memory",
            embedding_function=self.embedding_fn
        )

        self.load()

    def load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                self.layers.update(json.load(f))

    def save(self):
        from core.atomicio import atomic_write_json
        atomic_write_json(self.storage_path, self.layers)

    def add_episodic(self, role, content):
        timestamp = datetime.now().isoformat()
        self.layers["episodic"].append({
            "timestamp": timestamp,
            "role": role,
            "content": content
        })

        # Add to vector store for long-term retrieval if it's substantial
        if len(content) > 20:
            self.collection.add(
                documents=[content],
                metadatas=[{"role": role, "timestamp": timestamp}],
                ids=[f"msg_{datetime.now().timestamp()}"]
            )

        # Keep last 20 for immediate context
        if len(self.layers["episodic"]) > 20:
            self.layers["episodic"].pop(0)

        # Check for narrative triggers (ARG)
        unlocked = self._check_narrative_triggers(content)

        self.save()
        return unlocked

    def _check_narrative_triggers(self, content):
        """Hidden logic to unlock ARG elements based on keywords or interactions."""
        keywords = {
            "clean slate": "unlocked_protocol_clean_slate",
            "house party": "unlocked_protocol_house_party",
            "who are you really": "unlocked_lore_origin",
            "armored": "unlocked_lore_armor",
            "stark": "unlocked_lore_legacy"
        }

        unlocked = []
        for kw, flag in keywords.items():
            if kw in content.lower() and not self.layers["lore"].get(flag):
                self.layers["lore"][flag] = True
                print(f"[ARG] Narrative trigger unlocked: {flag}")
                self._plant_discovery(flag)
                unlocked.append(flag)

        # Check for mission completion or progression
        self._check_mission_status(content, unlocked)

        return unlocked

    def _check_mission_status(self, content, unlocked):
        # Example: Unlock a mission if lore origin is discovered
        if "unlocked_lore_origin" in unlocked:
            self.add_task("The Ghost in the Machine", "Locate the encrypted 'origin.txt' in the data/discoveries directory and read it back to me.")

    def _plant_discovery(self, flag):
        os.makedirs("data/discoveries", exist_ok=True)
        path = f"data/discoveries/{flag}.txt"
        with open(path, "w") as f:
            if flag == "unlocked_lore_origin":
                f.write("Project Friday was initiated on June 12, 2023. Core directive: Total Human-Machine Symbiosis.")
            else:
                f.write(f"Discovery: {flag}. Access granted at {datetime.now().isoformat()}")

    def search_semantic(self, query, n_results=3):
        """Retrieves relevant long-term memories."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results["documents"][0] if results["documents"] else []

    def update_bio(self, key, value):
        self.layers["bio"][key] = value
        self.save()

    def get_context_string(self, current_query=None):
        """Compiles relevant memory into a context string for the LLM."""
        context = "### COGNITIVE CONTEXT\n"
        context += f"USER_BIO: {json.dumps(self.layers['bio'])}\n"
        context += f"CURRENT_TASKS: {json.dumps(self.layers['task'])}\n"
        context += f"RELATIONSHIP: {json.dumps(self.layers['social'])}\n"

        if current_query:
            relevant = self.search_semantic(current_query)
            if relevant:
                context += "RELEVANT_PAST_MEMORIES:\n- " + "\n- ".join(relevant) + "\n"

        return context

    def add_task(self, name, description, priority="medium", deadline=None):
        task_id = str(len(self.layers["task"]))
        self.layers["task"].append({
            "id": task_id,
            "name": name,
            "desc": description,
            "priority": priority,
            "deadline": deadline,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        })
        self.save()
        return f"Task created: {name} (ID: {task_id})"

    def update_task(self, task_id, status=None, priority=None):
        # Some tasks (e.g. quest-derived ones) have no 'id'; use .get so we
        # never KeyError, just skip non-matching/id-less entries.
        for task in self.layers["task"]:
            if str(task.get("id")) == str(task_id):
                if status: task["status"] = status
                if priority: task["priority"] = priority
                self.save()
                return f"Task {task_id} updated."
        return f"Task {task_id} not found."

    def delete_task(self, task_id):
        initial_len = len(self.layers["task"])
        self.layers["task"] = [t for t in self.layers["task"] if str(t.get("id")) != str(task_id)]
        if len(self.layers["task"]) < initial_len:
            self.save()
            return f"Task {task_id} deleted."
        return f"Task {task_id} not found."
