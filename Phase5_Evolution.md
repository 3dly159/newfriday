# Implementation Plan: Phase 5 - Orchestration & Evolution

The final phase introduces multi-agent coordination, autonomous self-improvement, and the narrative "ARG" elements.

## 1. Milestone: The Legion Protocol (Multi-Agent)
*   **Task 1: Orchestration Logic.**
    *   Implement the "Task-Broker" pattern in the backend.
    *   Create specialized agent profiles: "Scout" (Search), "Architect" (Code), "Relay" (Comms).
*   **Task 2: Inter-Agent Communication.**
    *   Develop the JSON protocol for task handoffs and reporting.
    *   Ensure "Prime" (Friday) is the only agent with a voice.
*   **Task 3: Task-Level Parallelism.**
    *   Allow Friday to spawn a "Scout" agent in the background to research while she continues talking to the user.

## 2. Milestone: Autonomous Self-Improvement
*   **Task 1: Codebase Mapping.**
    *   Implement the "Architectural Memory" layer by indexing the project's own source files.
*   **Task 2: Refactoring Loop.**
    *   Implement a tool that allows the LLM to propose edits to its own Python files.
*   **Task 3: Automated Safety Checks.**
    *   Integrate a local test-runner (e.g., `pytest`).
    *   The self-improvement module must create a backup, run the tests on the new code, and only commit the changes if tests pass.

## 3. Milestone: ARG & Discovery Mechanics
*   **Task 1: Mystery Discovery Logic.**
    *   Plant "Easter Eggs" in the filesystem that Friday "discovers" over time based on user interaction levels.
*   **Task 2: Narrative Glitches.**
    *   Implement "Glitch" effects in the Three.js UI (e.g., flickering nodes in the Neural Map) to signal plot-driven data decryption.
*   **Task 3: Stark Protocols.**
    *   Implement the "Clean Slate" and "House Party" protocols (complex multi-step automation sequences).

## 4. Verification Criteria
*   [ ] Friday can research a complex topic in the background using a "Scout" agent and report back during the same session.
*   [ ] Friday successfully refactors a small utility function in its own codebase (verified via git diff).
*   [ ] The UI displays a "Glitch" effect when Friday discovers a specific narrative file.
*   [ ] The "Clean Slate Protocol" correctly closes all specified apps and clears the workspace.

## 5. Final Project Handover
*   **Task:** Conduct a full system stress test and performance audit.
*   **Task:** Finalize the developer documentation and user "Operations Manual."
