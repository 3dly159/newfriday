# Implementation Plan: Phase 2 - Interaction & Identity

This phase transforms Friday from a simple loop into a high-performance, charismatic assistant with a movie-grade UI.

## 1. Milestone: The Glass Shell (UI Chrome)
*   **Task 1: Glassmorphism Layout.**
    *   Build the 56px fixed header with the "Friday" wordmark.
    *   Implement the status dot logic (Teal = Listening, Blue = Processing, Gray = Idle).
    *   Create the 266px activity panel (right-side) with a toggle to collapse to 36px.
    *   **Task 4: The Settings Panel.** Implement a modal glass-morphism overlay that exposes sliders and inputs for all Registry parameters (Voice, Model, Threshold, etc.).
*   **Task 2: UI Styling.**
    *   Apply `backdrop-filter: blur(14px)` and the specified `rgba` borders to all panels.
    *   Use the **Inter** font family across the UI.
*   **Task 3: Bottom Mic Bar.**
    *   Build the 64x64px mic button.
    *   Implement the CSS keyframe animation for the expanding pulse ring when `listening`.
    *   Add the `friday:mic-toggle` event dispatcher in `app.js`.

## 2. Milestone: Latency Optimization (Pipelining)
*   **Task 1: Server-Side Sentence Splitting.**
    *   Implement the "Hold-One-Ahead" algorithm (see PRD Section 9.1) in the FastAPI backend.
    *   Use an `AsyncIterator` to stream tokens from Claude.
*   **Task 2: TTS Pipelining.**
    *   For every sentence split, trigger an asynchronous `edge-tts` request.
    *   Assign a sequential `seq_id` to each segment.
*   **Task 3: Client-Side Audio Queue.**
    *   Implement the `audioQueue` and `pumpQueue()` logic in `app.js`.
    *   Ensure the `is_final` flag properly triggers the UI state change back to `idle`.

## 3. Milestone: Stark-Class Personality
*   **Task 1: Personality File (AGENT.md).**
    *   Draft the core personality file with sarcastic, deadpan, and "butler-style" examples.
    *   Inject this as a cached System Prompt.
*   **Task 2: Recency Voice Cues.**
    *   In the backend, implement the logic to append the `[VOICE CUE]` string to the last user message in the API payload.
*   **Task 3: MCU Voice Profiles.**
    *   Add a toggle in the UI settings to switch between "The Butler" (British Male) and "The Boss" (Irish Female) voices in the `edge-tts` engine.

## 4. Verification Criteria
*   [ ] User hears the first word of Friday's response within ~1.5s of finishing their turn.
*   [ ] Response audio is continuous and gapless between sentences.
*   [ ] Friday's voice exhibits sarcastic wit and a "butler" tone (e.g., uses "Sir" or "Miss").
*   [ ] UI status indicators and mic animations reflect the system state accurately.
