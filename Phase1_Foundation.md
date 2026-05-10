# Implementation Plan: Phase 1 - The Foundation

This phase focuses on establishing the core environment, the visual identity of Friday, and the basic voice-in/voice-out loop.

## 1. Environment Setup
*   **Backend:** Initialize a Python 3.11+ environment. Install `fastapi`, `uvicorn`, `python-dotenv`.
*   **Frontend:** Create a `ui/` directory with `index.html`, `style.css`, and `app.js`. Use an import map for Three.js (v0.174).
*   **STT Engine:** Install `faster-whisper`. Download the `base.en` model.
*   **TTS Engine:** Install `edge-tts`.
*   **Directory Structure:**
    ```text
    friday-ai/
    ├── core/
    ├── ui/
    ├── data/
    └── .env
    ```

## 2. Milestone: The Luminous Orb
*   **Task 1: The Cosmic Canvas.** Implement a full-viewport Three.js scene with a dark background (`#0E0F13`).
*   **Task 2: The Nebula Shader.** Create a `PlaneGeometry` or use a custom shader on a large sphere to simulate drifting teal and purple nebula clouds using Simplex Noise.
*   **Task 3: The Core Orb.**
    *   Implement `SphereGeometry` at the center.
    *   Write the custom `ShaderMaterial` for the inner core and halo (see PRD Section 8.1).
    *   Expose the `uVoiceBright` uniform.
*   **Task 4: Post-Processing.** Add `EffectComposer` with `RenderPass` and `UnrealBloomPass`.

## 3. Milestone: The Basic Voice Loop
*   **Task 1: Audio Capture.** Implement a `MediaRecorder` in `app.js` to capture user microphone input and stream it via WebSockets to the backend.
*   **Task 2: STT Integration.**
    *   In the backend, process the incoming audio chunks.
    *   Use `Faster-Whisper` to transcribe the audio once a silence gap is detected.
*   **Task 3: Simple LLM Response.** Connect the transcription to a base Claude model (Anthropic SDK) to get a text response.
*   **Task 4: TTS Generation.**
    *   Use `edge-tts` to convert the LLM text into a `.mp3` or `.wav` stream.
    *   Send the audio bytes back to the frontend.
*   **Task 5: Orb Reactivity.** In `app.js`, use the `Web Audio API` to analyze the frequency of the returning TTS audio and map the amplitude to the `uVoiceBright` uniform (0.0 to 1.0).

## 4. Verification Criteria
*   [ ] The browser displays a glowing teal orb on a cosmic background.
*   [ ] The orb pulses gently (4s cycle) when idle.
*   [ ] Speaking to the microphone results in a text transcription in the console.
*   [ ] Friday responds with audio, and the orb's brightness intensifies in sync with the speech.
