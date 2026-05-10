# Implementation Plan: Phase 3 - System Mastery

This phase gives Friday "hands" to manipulate the machine and a mechanism to learn new skills.

## 1. Milestone: Deep System Integration (The Bridge)
*   **Task 1: The HID Bridge.**
    *   Install `PyAutoGUI`.
    *   Create a "Bridge" module in the backend that exposes `move_mouse`, `click`, and `type_text` as functions.
*   **Task 2: Application Orchestration.**
    *   Implement OS-specific commands (e.g., `open` on macOS, `start` on Windows) to launch and terminate apps.
*   **Task 3: Secure Script Engine.**
    *   Implement a tool that allows the LLM to write a Python or Bash script to a temporary file and execute it.
    *   Add a "Safety Interlock" system: any script that requires network access or file deletion must be flagged in the UI for user approval before running.

## 2. Milestone: Dynamic Skill Acquisition
*   **Task 1: The Skill Manifest.**
    *   Define the `skill.json` format (see PRD Section 10.2).
    *   Create a local `skills/` folder with an initial "System Control" skill.
*   **Task 2: Clawhub Integration.**
    *   Implement an API client to fetch skill manifests from `clawhub.io` (mocked until public API is live).
*   **Task 3: Dynamic Tool Loading.**
    *   Implement a logic in `brain.py` that allows Friday to "decide" she needs a new skill, fetch the manifest, and update the LLM's tool-list on the next turn.

## 3. Milestone: The Stark HUD
*   **Task 1: System Vitals Component.**
    *   Implement a background process that monitors CPU, RAM, and Battery.
    *   Create floating biometric-style bars in the UI showing "Suit Integrity" (system health).
*   **Task 2: Targeting Reticles.**
    *   Implement a Three.js overlay that renders subtle targeting rings following the mouse cursor.
    *   Add "Lock-on" animations when Friday is performing a system action.

## 4. Verification Criteria
*   [ ] Friday can open a specific application (e.g., "Friday, open VS Code") upon request.
*   [ ] Friday can perform a mouse action (e.g., "Friday, move my mouse to the top right").
*   [ ] The UI shows real-time CPU/RAM vitals in a HUD-style display.
*   [ ] Friday can explain a skill she doesn't currently have and "install" it from the repository.
