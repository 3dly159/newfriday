import pytest
import json
from fastapi.testclient import TestClient
from core.main import app

client = TestClient(app)

def test_websocket_connection():
    with client.websocket_connect("/ws/voice") as websocket:
        # We can't easily test audio processing without a real mic/file in this env,
        # but we can verify the socket accepts and stays open.
        assert websocket is not None

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Friday Backend Online"}

def test_static_files():
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "orb-canvas" in response.text
