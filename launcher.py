import os
import sys
import subprocess
import time
import platform
import json

def check_dependencies():
    print("Checking dependencies...")
    try:
        import fastapi
        import uvicorn
        import faster_whisper
        import edge_tts
        import chromadb
        # import pyautogui # Wrapped in bridge
        import psutil
        import cv2
        from PIL import Image
        print("✅ Core dependencies found.")
    except (ImportError, KeyError) as e:
        print(f"❌ Missing dependency: {e.name}")
        print("Running: pip install -r requirements.txt")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def check_env():
    print("Checking environment...")
    if not os.path.exists("config/registry.json"):
        print("⚠️ Warning: config/registry.json not found. Creating default.")
        os.makedirs("config", exist_ok=True)
        default_registry = {
            "model_provider": "anthropic",
            "llm_model": "claude-3-5-sonnet-20241022",
            "voice_profile": "en-GB-RyanNeural",
            "proactive_interval": 15,
            "theme_color": "#2DD4AB"
        }
        with open("config/registry.json", "w") as f:
            json.dump(default_registry, f, indent=4)

    if "ANTHROPIC_API_KEY" not in os.environ:
        print("⚠️ Warning: ANTHROPIC_API_KEY environment variable not set.")
        print("Friday will run in 'Blackout' mode with limited intelligence unless a local provider is configured.")

def start_friday():
    print("\n🚀 Initializing Friday AI...")
    print(f"Platform: {platform.system()} {platform.release()}")
    print("UI: http://localhost:8000")

    # Add project root to PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    try:
        # Launch the server
        cmd = [sys.executable, "-m", "uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000"]
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\n👋 Friday is standing down. Goodbye, Sir.")

if __name__ == "__main__":
    check_dependencies()
    check_env()
    start_friday()
