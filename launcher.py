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
        # import pyautogui # Moved to lazy loading in core/bridge.py
        import psutil
        import cv2
        from PIL import Image

        # Linux specific GUI dependencies
        if platform.system() == "Linux":
            try:
                import tkinter
            except ImportError:
                print("\n⚠️  Warning: 'tkinter' is missing.")
                print("   On Linux, Friday needs tkinter for UI automation (mouse/keyboard).")
                print("   Run: sudo apt-get install python3-tk")
                print("   (Note: Friday will continue to launch, but HID control will be disabled)\n")

            if "DISPLAY" not in os.environ:
                print("\n⚠️  Warning: 'DISPLAY' environment variable is not set.")
                print("   Friday is running in a headless environment.")
                print("   UI automation (mouse/keyboard) will be disabled.\n")

        print("✅ Core dependencies found.")
    except (ImportError, KeyError) as e:
        print(f"❌ Missing dependency: {getattr(e, 'name', str(e))}")
        print("Running: pip install -r requirements.txt")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def check_env():
    print("Checking environment...")
    if not os.path.exists("config/registry.json"):
        print("⚠️ Warning: config/registry.json not found. Creating default.")
        os.makedirs("config", exist_ok=True)
        default_registry = {
            "ai_logic": {
                "model_provider": "anthropic",
                "llm_model": "claude-3-5-sonnet-20241022"
            },
            "voice": {
                "voice_profile": "en-GB-RyanNeural"
            },
            "system": {
                "proactive_interval": 15,
                "theme_color": "#2DD4AB"
            }
        }
        with open("config/registry.json", "w") as f:
            json.dump(default_registry, f, indent=4)

    if "ANTHROPIC_API_KEY" not in os.environ:
        print("⚠️ Warning: ANTHROPIC_API_KEY environment variable not set.")
        print("Friday will run in 'Blackout' mode with limited intelligence unless a local provider is configured.")

def start_friday():
    print("\n🚀 Initializing Friday AI...")
    print(f"Platform: {platform.system()} {platform.release()}")
    print("UI Endpoint: http://localhost:8000")
    print("Note: If you see a 'MouseInfo' or 'tkinter' warning below, please ignore it. Friday is still starting...")

    # Add project root to PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    try:
        # Launch the server
        # We use a slight delay before printing final success to allow uvicorn to bind
        cmd = [sys.executable, "-m", "uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

        # On some Linux systems, pyautogui's dependency 'MouseInfo' prints a note
        # that looks like an error but isn't blocking.
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\n👋 Friday is standing down. Goodbye, Sir.")

if __name__ == "__main__":
    check_dependencies()
    check_env()
    start_friday()
