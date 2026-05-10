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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Friday")

active_connections: list[WebSocket] = []

# Initialize modules
brain = FridayBrain()
stt = FridaySTT()
tts = FridayTTS()

async def thought_cycle():
    """Background loop for proactive thinking."""
    while True:
        try:
            # Think every 20 minutes (configurable in registry)
            with open("config/registry.json", "r") as f:
                config = json.load(f)
            interval = config.get("system", {}).get("proactive_interval", 20) * 60

            await asyncio.sleep(interval)

            logger.info(f"[{datetime.now().isoformat()}] Friday is contemplating...")

            # Example: Proactive check on system load
            from core.bridge import FridayBridge
            bridge = FridayBridge()
            vitals = bridge.get_system_vitals()
            if vitals["cpu_percent"] > 80:
                msg = "Sir, CPU load is quite high. You might want to check the background processes."
                await broadcast_proactive_message(msg)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in thought cycle: {e}")
            await asyncio.sleep(60)

async def broadcast_proactive_message(message: str):
    """Broadcasts a message to all connected UIs."""
    if not active_connections:
        return

    output_path = f"data/logs/proactive_{uuid.uuid4().hex}.mp3"
    await tts.generate_speech(message, output_path)

    with open(output_path, "rb") as f:
        audio_bytes = f.read()

    payload = {
        "type": "speak_segment",
        "text": message,
        "is_final": True
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
    thought_task = asyncio.create_task(thought_cycle())
    yield
    # Shutdown logic
    thought_task.cancel()
    try:
        await thought_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# Mount UI
app.mount("/static", StaticFiles(directory="ui"), name="static")

@app.get("/")
async def get_index():
    return {"message": "Friday Backend Online"}

@app.get("/api/config")
async def get_config():
    with open("config/registry.json", "r") as f:
        return json.load(f)

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

def is_sentence_end(text):
    return text.strip().endswith(('.', '?', '!'))

async def process_and_send_segment(websocket, text, is_final):
    output_path = f"data/logs/resp_{uuid.uuid4().hex}.mp3"
    await tts.generate_speech(text, output_path)

    with open(output_path, "rb") as f:
        audio_bytes = f.read()

    await websocket.send_json({
        "type": "speak_segment",
        "text": text,
        "is_final": is_final
    })
    await websocket.send_bytes(audio_bytes)
    if os.path.exists(output_path):
        os.remove(output_path)

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            temp_filename = f"data/logs/chunk_{uuid.uuid4().hex}.wav"
            with open(temp_filename, "wb") as f:
                f.write(data)

            transcription = stt.transcribe(temp_filename)
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

            if not transcription:
                continue

            await websocket.send_json({"type": "status", "state": "processing"})

            # Streaming Pipelining (Hold-One-Ahead)
            held_sentence = None
            current_buffer = ""

            async for token in brain.get_streaming_response(transcription):
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
