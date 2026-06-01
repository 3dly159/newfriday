import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from core.brain import FridayBrain
from core.stt import FridaySTT
from core.tts import FridayTTS
from core.proactive import ProactiveEngine
from core.voice_session import VoiceSession

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Friday")

active_connections: list[WebSocket] = []

# Initialize modules
brain = FridayBrain()
stt = FridaySTT()
tts = FridayTTS()
proactive = ProactiveEngine(brain)

async def broadcast_proactive_message(message: str):
    """Broadcasts a proactive message to all connected UIs using the v2 event
    contract (mood + state + transcript + caption + audio), so it shows captions
    and pulses the orb like a normal turn."""
    if not active_connections:
        return
    mood_cfg = brain.personality.mood_states[brain.personality.current_mood]
    output_path = f"data/logs/proactive_{uuid.uuid4().hex}.mp3"
    try:
        _, words = await tts.generate_speech_timed(message, output_path)
        with open(output_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        logger.error(f"Proactive TTS error: {e}")
        words, audio_bytes = [], b""

    seg_id = uuid.uuid4().hex
    for connection in active_connections:
        try:
            await connection.send_json({"type": "mood", "mood": brain.personality.current_mood,
                                        "orb_color": mood_cfg["orb_color"]})
            await connection.send_json({"type": "state", "state": "speaking"})
            await connection.send_json({"type": "transcript", "role": "friday",
                                        "text": message, "final": True})
            await connection.send_json({"type": "caption", "segment_id": seg_id,
                                        "mode": "word" if words else "sentence",
                                        "words": words, "text": message})
            if audio_bytes:
                await connection.send_bytes(audio_bytes)
            await connection.send_json({"type": "state", "state": "idle"})
        except Exception:
            pass

    if os.path.exists(output_path):
        os.remove(output_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    os.makedirs("data/logs", exist_ok=True)
    proactive_task = asyncio.create_task(proactive.start(broadcast_proactive_message))
    yield
    # Shutdown logic
    proactive.stop()
    proactive_task.cancel()
    try:
        await proactive_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def get_index():
    from fastapi.responses import FileResponse
    return FileResponse("ui/index.html")

@app.get("/favicon.ico")
async def favicon():
    # Avoid a noisy 404 in the browser console; we have no icon asset.
    from fastapi.responses import Response
    return Response(status_code=204)

# Static files should be mounted at a specific path if we have API routes
app.mount("/ui", StaticFiles(directory="ui"), name="static")

@app.get("/api/config")
async def get_config():
    with open("config/registry.json", "r") as f:
        config = json.load(f)
    # Inject memory state for UI sync
    config["system_memory"] = brain.memory.layers
    return config

@app.get("/api/vitals")
async def get_vitals():
    from core.bridge import FridayBridge
    bridge = FridayBridge()
    return bridge.get_system_vitals()

@app.get("/api/health")
async def get_health():
    """Reports whether the configured LLM brain is reachable."""
    return await brain.health_check()

@app.post("/api/config")
async def update_config(config: dict):
    # Validate against the schema before touching disk, so malformed input
    # (e.g. "[object Object]" or out-of-range values) can't corrupt the registry.
    from fastapi.responses import JSONResponse
    from core.config import validate_config, save_config
    ok, errors, cleaned = validate_config(config)
    if not ok:
        return JSONResponse(status_code=422, content={"status": "invalid", "errors": errors})
    save_config(cleaned)
    # Re-initialize modules with new config
    global brain, stt, tts
    brain = FridayBrain()
    stt = FridaySTT()
    tts = FridayTTS()
    return {"status": "success"}

@app.get("/api/permissions")
async def get_permissions():
    from core.bridge import FridayBridge
    bridge = FridayBridge()
    return bridge.permissions.permissions

@app.post("/api/permissions")
async def update_permissions(perms: dict):
    from core.bridge import FridayBridge
    bridge = FridayBridge()
    bridge.permissions.permissions.update(perms)
    bridge.permissions.save()
    return {"status": "success"}

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    session = VoiceSession(
        brain=brain, stt=stt, tts=tts,
        send_json=websocket.send_json, send_bytes=websocket.send_bytes,
    )
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            # Text / control frames (JSON).
            if message.get("text") is not None:
                try:
                    ctrl = json.loads(message["text"])
                except (ValueError, TypeError):
                    continue
                if ctrl.get("type") == "interrupt":
                    print("[BARGE-IN] User interrupted Friday.")
                    continue
                if ctrl.get("type") == "text" and ctrl.get("content", "").strip():
                    user_text = ctrl["content"].strip()
                    print(f"[USER/text] {user_text}")
                    unlocked = brain.memory.add_episodic("user", user_text)
                    if unlocked:
                        await websocket.send_json({"type": "arg_unlocked", "flags": unlocked})
                    await session.run_turn(user_text)
                continue

            data = message.get("bytes")
            if not data:
                continue

            # Audio frame -> STT. The browser sends WebM/Opus.
            temp_filename = f"data/logs/chunk_{uuid.uuid4().hex}.webm"
            os.makedirs("data/logs", exist_ok=True)
            with open(temp_filename, "wb") as f:
                f.write(data)
            try:
                transcription = stt.transcribe(temp_filename)
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                transcription = ""
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

            if not transcription:
                continue
            print(f"\n[TRANSCRIPTION] {transcription}")

            mode = brain.config.get("speech", {}).get("interaction_mode", "wake_word")
            is_addressed = any(kw in transcription.lower() for kw in ["friday", "hey friday", "computer"])
            is_greeting = any(transcription.lower().strip() == g for g in ["hello", "good morning", "good evening", "hi friday"])

            if mode == "wake_word" and not is_addressed and not is_greeting:
                print(f"[BACKGROUND] Recorded: {transcription}")
                brain.memory.add_episodic("background", transcription)
                continue

            print(f"[USER] {transcription}")
            unlocked = brain.memory.add_episodic("user", transcription)
            if unlocked:
                await websocket.send_json({"type": "arg_unlocked", "flags": unlocked})
            await session.run_turn(transcription)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in voice loop: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
