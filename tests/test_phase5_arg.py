import pytest
import os
from core.memory import FridayMemory

def test_narrative_triggers():
    # Use a temporary memory file for testing
    test_path = "data/test_memory_arg.json"
    if os.path.exists(test_path): os.remove(test_path)

    memory = FridayMemory(storage_path=test_path, vector_db_path="data/test_vector_db_arg")

    # Trigger Lore Discovery
    memory.add_episodic("user", "Friday, who are you really?")

    assert memory.layers["lore"].get("unlocked_lore_origin") is True
    assert os.path.exists("data/discoveries/unlocked_lore_origin.txt")

    # Trigger Protocol Discovery
    memory.add_episodic("user", "Initiate clean slate.")
    assert memory.layers["lore"].get("unlocked_protocol_clean_slate") is True

    # Cleanup
    if os.path.exists(test_path): os.remove(test_path)
    # Note: ChromaDB cleanup is harder, but we'll leave it for now.
