# Implementation Plan: Phase 6 - Hardening & Distribution

This phase prepares Friday for real-world deployment, focusing on reliability, resource efficiency, and secure distribution.

## 1. Milestone: Performance & Resource Tuning
*   **Task 1: Latency Profiling.**
    *   Measure the end-to-end delay for each component: STT -> LLM -> TTS -> Audio Playback.
    *   Identify and remove any remaining serial bottlenecks in the pipeline.
*   **Task 2: Resource Footprint.**
    *   Optimize the Three.js render loop to reduce GPU/CPU usage when the window is inactive.
    *   Implement "Sleep" states for the background Thought Cycle when the laptop is on battery power.
*   **Task 3: VAD Calibration.**
    *   Fine-tune the Voice Activity Detection (VAD) threshold to handle noisy environments (e.g., coffee shops or fans).

## 2. Milestone: Security Hardening
*   **Task 1: Permission Sandboxing.**
    *   Implement a robust permission manifest for each skill.
    *   Users must be able to toggle "Read Only", "Write Files", and "HID Control" on a per-session or per-skill basis.
*   **Task 2: Secure Key Management.**
    *   Ensure all API keys (Anthropic, Edge TTS, etc.) are stored in a secure local vault or OS-level Keychain, never in plaintext.
*   **Task 3: Privacy Audit.**
    *   Verify that audio buffers from the Sensory Memory layer are purged from memory immediately after transcription.

## 3. Milestone: Distribution & Installation
*   **Task 1: Packaging (Electron/Native).**
    *   Wrap the UI and Backend into a single distributable package (e.g., using Electron or a custom Python/JS bundle).
*   **Task 2: Dependency Installer.**
    *   Create an automated installer that handles Python requirements, system-level audio drivers, and local Whisper model downloads.
*   **Task 3: Update Mechanism.**
    *   Implement a "Self-Update" protocol (similar to the self-improvement module) that allows Friday to download and apply official patches.

## 4. Verification Criteria
*   [ ] Friday consumes <5% CPU in idle state.
*   [ ] End-to-end latency for a 5-word response is <1.2 seconds.
*   [ ] User is prompted for approval when a new skill requests "HID Control" permissions.
*   [ ] The application installs and runs correctly on a clean machine using the provided installer.
