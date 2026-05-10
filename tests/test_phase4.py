import pytest
import os
import shutil
from core.memory import FridayMemory

import tempfile

@pytest.fixture
def memory():
    # Use a temp directory for tests
    tmpdir = tempfile.mkdtemp()
    test_db = os.path.join(tmpdir, "test_vector_db")
    test_json = os.path.join(tmpdir, "test_memory.json")
    if os.path.exists(test_db): shutil.rmtree(test_db)
    if os.path.exists(test_json): os.remove(test_json)

    mem = FridayMemory(storage_path=test_json, vector_db_path=test_db)
    yield mem

    # Cleanup
    if os.path.exists(test_db): shutil.rmtree(test_db)
    if os.path.exists(test_json): os.remove(test_json)

def test_semantic_memory(memory):
    memory.add_episodic("user", "My favorite color is teal.")
    memory.add_episodic("user", "I live in San Francisco.")

    results = memory.search_semantic("What color do I like?")
    assert any("teal" in doc.lower() for doc in results)

def test_context_string_retrieval(memory):
    memory.add_episodic("user", "I am a software engineer.")
    context = memory.get_context_string(current_query="What is my job?")
    assert "software engineer" in context
