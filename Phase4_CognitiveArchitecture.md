# Implementation Plan: Phase 4 - Cognitive Architecture

This phase implements the "Brain" of Friday, including layered memory and the ability to think independently.

## 1. Milestone: Layered Memory System
*   **Task 1: The Vector Store (Semantic Memory).**
    *   Initialize `ChromaDB` locally.
    *   Implement a background process that summarizes the conversation every 10 turns and stores the summary in the vector database.
    *   Integrate RAG (Retrieval-Augmented Generation) so Friday can recall facts from previous sessions.
*   **Task 2: Narrative & Episodic Logs.**
    *   Implement the `logs/episodes.jsonl` format to record major milestones and user interactions.
    *   Create a "Morning Briefing" generator that reads yesterday's logs.
*   **Task 3: Working Memory.**
    *   Optimize the sliding window context for the LLM to maintain coherent, long-running task threads.

## 2. Milestone: The Sentience Loop (Proactivity)
*   **Task 1: The Thought Cycle.**
    *   Implement a 15–30 minute background timer.
    *   When triggered, feed the current system state, pending tasks, and recent memories into the LLM with a "Thought Prompt."
*   **Task 2: The "Taken the Liberty" Protocol.**
    *   Allow the LLM to execute "low-stakes" system optimizations (e.g., clearing temp files) during a Thought Cycle.
    *   Implement the proactive voice trigger: Friday speaks to the user without being prompted if a "Thought" is deemed significant.

## 3. Milestone: Neural Pathway Visualization
*   **Task 1: Knowledge Graph Rendering.**
    *   Implement the hub-and-spoke 3D graph in Three.js (v0.174).
    *   Map the `nodes` and `edges` from the Semantic Memory categories (e.g., "User Preferences", "Project Nebula").
*   **Task 2: Visual Effects.**
    *   Add the core "breathe" shaders to nodes based on their "freshness" (recency).
    *   Implement flowing edge particles using a custom particle system or `PointsMaterial`.
*   **Task 3: Interaction.**
    *   Add hover tooltips using `CSS2DRenderer` to show details for each knowledge node.

## 4. Verification Criteria
*   [ ] Friday recalls a detail mentioned in a conversation from 2 days ago.
*   [ ] Friday proactively speaks (e.g., "Sir, I've noticed your battery is low and have taken the liberty of dimming your screen.").
*   [ ] The Neural Map UI correctly visualizes clusters of information from Friday's memory.
*   [ ] Friday provides a "Morning Briefing" summarizing recent activities upon startup.
