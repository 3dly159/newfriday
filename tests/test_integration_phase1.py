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
    assert "html" in response.text.lower()

def test_static_files():
    # Test mounting of ui directory
    response = client.get("/ui/js/app.js")
    assert response.status_code == 200
