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
    """Broadcasts a message to all connected UIs."""
    if not active_connections:
        return

    # Get current mood for TTS parameters
    mood_cfg = brain.personality.mood_states[brain.personality.current_mood]

    output_path = f"data/logs/proactive_{uuid.uuid4().hex}.mp3"
    # We could extend TTS to accept pitch/rate, for now we use Edge-TTS defaults
    await tts.generate_speech(message, output_path)

    with open(output_path, "rb") as f:
        audio_bytes = f.read()

    payload = {
        "type": "speak_segment",
        "text": message,
        "is_final": True,
        "mood": brain.personality.current_mood,
        "orb_color": mood_cfg["orb_color"]
    }

    for connection in active_connections:
        try:
            await connection.send_json(payload)
            await connection.send_bytes(audio_bytes)
        except:
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

@app.post("/api/config")
async def update_config(config: dict):
    with open("config/registry.json", "w") as f:
        json.dump(config, f, indent=4)
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

def is_sentence_end(text):
    return text.strip().endswith(('.', '?', '!'))

async def process_and_send_segment(websocket, text, is_final):
    output_path = f"data/logs/resp_{uuid.uuid4().hex}.mp3"
    try:
        await tts.generate_speech(text, output_path)

        with open(output_path, "rb") as f:
            audio_bytes = f.read()

        await websocket.send_json({
            "type": "speak_segment",
            "text": text,
            "is_final": is_final
        })
        await websocket.send_bytes(audio_bytes)
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        # Still send text so user can read it even if audio fails
        await websocket.send_json({
            "type": "speak_segment",
            "text": text,
            "is_final": is_final,
            "error": "TTS_FAILED"
        })
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            # The browser sends WebM/Opus data usually. Faster-Whisper can often handle it if extension is correct or via ffmpeg
            temp_filename = f"data/logs/chunk_{uuid.uuid4().hex}.webm"
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

            # Log transcription
            print(f"\n[TRANSCRIPTION] {transcription}")

            # Check interaction mode from registry
            mode = brain.config.get("speech", {}).get("interaction_mode", "wake_word")

            # Wake Word / Direct Address Check
            # Requirement: "listen all the time interact only if words are addressed to it"
            is_addressed = any(kw in transcription.lower() for kw in ["friday", "hey friday", "computer"])

            # Contextual greeting exception (always allow responses to simple greetings)
            is_greeting = any(transcription.lower().strip() == g for g in ["hello", "good morning", "good evening", "hi friday"])

            if mode == "wake_word" and not is_addressed and not is_greeting:
                # Still record to episodic memory for "background awareness" but don't respond
                print(f"[BACKGROUND] Recorded: {transcription}")
                brain.memory.add_episodic("background", transcription)
                continue

            print(f"[USER] {transcription}")

            # Update Memory & Check ARG triggers
            unlocked = brain.memory.add_episodic("user", transcription)
            if unlocked:
                await websocket.send_json({"type": "arg_unlocked", "flags": unlocked})

            await websocket.send_json({"type": "status", "state": "processing"})

            # Streaming Pipelining (Hold-One-Ahead)
            held_sentence = None
            current_buffer = ""

            full_reply = ""
            print("[FRIDAY] ", end="", flush=True)
            async for token in brain.get_streaming_response(transcription):
                full_reply += token
                print(token, end="", flush=True)

                # Filter out system notifications from the TTS pipeline
                if token.startswith("[System:"):
                    await websocket.send_json({
                        "type": "status",
                        "state": "processing",
                        "notification": token
                    })
                    continue

                current_buffer += token
                if is_sentence_end(current_buffer):
                    if held_sentence:
                        await process_and_send_segment(websocket, held_sentence, is_final=False)
                    held_sentence = current_buffer
                    current_buffer = ""

            # Flush the final held sentence
            final_text = (held_sentence or "") + current_buffer
            if final_text.strip():
                await process_and_send_segment(websocket, final_text, is_final=True)
            print() # End Friday line

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
