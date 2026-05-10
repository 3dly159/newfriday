import os
import json
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from core.brain import FridayBrain
from core.stt import FridaySTT
from core.tts import FridayTTS

app = FastAPI()

# Initialize modules
brain = FridayBrain()
stt = FridaySTT()
tts = FridayTTS()

# Mount UI
app.mount("/static", StaticFiles(directory="ui"), name="static")

@app.get("/")
async def get_index():
    return {"message": "Friday Backend Online"}

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive audio data from frontend
            data = await websocket.receive_bytes()

            # Temporary file for the chunk
            temp_filename = f"data/logs/chunk_{uuid.uuid4().hex}.wav"
            with open(temp_filename, "wb") as f:
                f.write(data)

            # 1. STT
            transcription = stt.transcribe(temp_filename)
            if not transcription:
                os.remove(temp_filename)
                continue

            # 2. Brain
            response_text = await brain.get_response(transcription)

            # 3. TTS
            output_tts_path = f"data/logs/resp_{uuid.uuid4().hex}.mp3"
            await tts.generate_speech(response_text, output_tts_path)

            # 4. Send back to frontend
            with open(output_tts_path, "rb") as f:
                audio_bytes = f.read()

            await websocket.send_json({
                "type": "response",
                "text": response_text,
                "transcription": transcription
            })
            await websocket.send_bytes(audio_bytes)

            # Cleanup
            os.remove(temp_filename)
            os.remove(output_tts_path)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in voice loop: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
