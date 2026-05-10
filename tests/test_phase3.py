import pytest
from fastapi.testclient import TestClient
from core.main import app
from core.bridge import FridayBridge

client = TestClient(app)

def test_vitals_endpoint():
    response = client.get("/api/vitals")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_usage" in data
    assert "memory_usage" in data

def test_bridge_vitals():
    bridge = FridayBridge()
    vitals = bridge.get_system_vitals()
    assert isinstance(vitals["cpu_usage"], float)
    assert isinstance(vitals["memory_usage"], float)

def test_brain_tools_initialization():
    from core.brain import FridayBrain
    brain = FridayBrain()
    assert len(brain.tools) > 0
    assert any(t["name"] == "open_app" for t in brain.tools)
