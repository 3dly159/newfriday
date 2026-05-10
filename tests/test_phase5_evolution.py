import os
import pytest
from core.bridge import FridayBridge

def test_source_management():
    bridge = FridayBridge()
    bridge.permissions.permissions["file_system_write"] = "allow"
    test_file = "data/test_refactor.txt"
    content = "original content"

    # Write
    result = bridge.write_source(test_file, content)
    assert "Successfully wrote" in result
    assert os.path.exists(test_file)

    # Read
    read_content = bridge.read_source(test_file)
    assert read_content == content

    # Refactor with backup
    new_content = "new content"
    bridge.write_source(test_file, new_content, backup=True)
    assert os.path.exists(f"{test_file}.bak")
    assert bridge.read_source(test_file) == new_content

    # Cleanup
    os.remove(test_file)
    os.remove(f"{test_file}.bak")

def test_run_tests():
    bridge = FridayBridge()
    # Run a simple test
    result = bridge.run_tests("tests/test_phase5_legion.py")
    assert "Test Results" in result
    assert "passed" in result
