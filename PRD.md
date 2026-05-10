# Product Requirements Document (PRD): Friday AI

## 1. Project Overview
**Friday** is a next-generation, Voice-First AI based Augmented Reality Game (ARG) and personal assistant. Unlike traditional reactive assistants, Friday is proactive, self-evolving, and possesses deep integration with the host machine. It is designed to feel like a living entity inhabiting the user's computer, capable of autonomous thought, multi-agent orchestration, and physical interaction (simulated via mouse/keyboard control).

### 1.1 Vision
To create an immersive, sentient-feeling AI companion that blurs the line between software and digital life, providing unparalleled utility through proactive engagement and complex task automation.

---

## 2. User Experience & Visual Interface

### 2.1 Visual Assets & 3D Scenes

#### 2.1.1 The Luminous Orb & Cosmic Background
The primary UI is a full-viewport Three.js scene that serves as the "face" of Friday.

*   **Background:**
    *   Base Color: `#0E0F13` (Dark Cosmic).
    *   Elements: Slowly drifting nebula clouds in teal, purple, and blue wisps.
    *   Technique: Noise-based shaders or layered radial gradients.
    *   Atmosphere: Subtle twinkling starfield.
*   **The Orb (The "Brain"):**
    *   Location: Center of the viewport.
    *   Color: Luminous teal (`#2DD4AB`).
    *   Layers:
        1.  Wide soft atmospheric bloom.
        2.  Medium halo.
        3.  Bright inner core.
    *   Rendering: Additive blending and bloom post-processing for a true glow effect.
*   **Animations & Interactivity:**
    *   **Idle State:** Gentle sine-wave pulse (approx. 4s cycle) to simulate breathing.
    *   **Voice Activity:** Intensification of the inner core and halo driven by audio amplitude.
    *   **Uniform Control:** Expose `uVoiceBright` (0.0 – 1.0) to dynamically adjust glow intensity based on Friday’s speech or user input.
    *   **Layering:** Canvas covers full viewport at `z-index: 1`.

#### 2.1.2 Neural Pathway Visualization
A 3D hub-and-spoke graph representing Friday's connected knowledge sources.

*   **Technology:** Three.js (v0.174) with `OrbitControls`, `EffectComposer`, `RenderPass`, `UnrealBloomPass`, and `CSS2DRenderer`.
*   **Data Model:** JSON input `{nodes, edges}`.
    *   **Node Types:** `hub` (origin), `category` (first ring), `leaf` (outer cluster).
    *   **Attributes:** `id`, `type`, `label`, `color`, `freshness`, `detail`.
*   **Visual Representation:**
    *   **Nodes:** Shader-driven core spheres that "breathe" based on freshness, wrapped in a translucent halo.
    *   **Connections:** Thin lines with flowing edge particles, color-coded by category.
    *   **Background:** Pitch-black with a starfield, soft nebula backdrop, and drifting ambient particles.
*   **Interaction:**
    *   `OrbitControls` with auto-rotate.
    *   `CSS2DRenderer` for HTML labels on hub and categories.
    *   `Raycaster` for hover tooltips showing labels and detailed metadata.
*   **Atmosphere:** High-intensity glow via `UnrealBloomPass`.

### 2.2 The Glass Shell (UI Chrome)
Information is layered onto the 3D scene using a glassmorphism UI shell that floats over the orb.

*   **Styling:**
    *   Font: **Inter**.
    *   Accent Color: `#2DD4AB` (Teal).
    *   Surface: `rgba(14, 15, 19, 0.15)` with `backdrop-filter: blur(14px)` and a 1px border of `rgba(255, 255, 255, 0.06)`.
*   **Components:**
    1.  **Fixed Header (56px):**
        *   Left: "Friday" wordmark with a small teal dot.
        *   Right: Three ghost icon buttons (Neural Map, Alerts with badge, Settings).
        *   Status Indicator: 10px status dot.
            *   Teal (pulsing): Listening.
            *   Blue/Purple: Processing.
            *   Gray: Idle.
    2.  **Activity Panel (266px, Right-side):**
        *   Sections: Inbox Replies, Scout Tasks, Flux Tasks, Relay Drafts.
        *   Headers: Uppercase 10px with counts.
        *   Animations: Entries slide in from right (300ms, `cubic-bezier(0.16, 1, 0.3, 1)`).
        *   Behavior: Collapsible to 36px via toggle.
    3.  **Floating Response Cards (240px wide / 388px for revenue):**
        *   Design: 2px teal top accent bar, `rgba(22, 23, 29, 0.75)` background, 16px blur.
        *   Animation: Entry rotation (`rotateX(8deg)`) and a gentle vertical float (+6px, 4s loop).
*   **Interactivity:** Overlays use `pointer-events: auto` only where needed so the underlying 3D canvas remains interactive.

### 2.3 The Bottom Mic Control Bar
The primary interaction point for manual voice triggering.

*   **Design:** Fixed bottom bar, transparent (`pointer-events: none`).
*   **Mic Button (64x64px circular):**
    *   **Idle:** Dark circle (`#16171D`), 1px white border (`rgba(255, 255, 255, 0.08)`), white microphone SVG.
    *   **Active (Listening):** Teal border (`#2DD4AB`), white stop square icon, glowing box-shadow (0 0 24px `#2DD4AB80`).
    *   **Animation:** Expanding pulse ring (0-10px spread, opacity 1-0, 1.4s infinite, `cubic-bezier(0.16, 1, 0.3, 1)`).
*   **Hint Text:** 11px uppercase hint below button (`rgba(255,255,255,0.4)`, letter-spacing 0.08em), e.g., "TAP OR 'HEY FRIDAY'".
*   **Events:** Toggling the state dispatches a `friday:mic-toggle` custom event.

### 2.4 Interaction Model
*   **Voice-First:** Primary interaction is spoken language.
*   **Always-On Listening:** Friday listens continuously but only responds when addressed or when it has a proactive thought to share.
*   **Proactivity:** Friday can initiate conversations based on scheduled tasks, system events, or internal "thought" cycles.

---

## 3. Core Functionalities

### 3.1 Proactive Autonomy
*   **Self-Initiated Talk:** Friday does not wait for a wake word to speak if it has relevant information or questions.
*   **System Awareness:** Monitors system health, files, and background processes to provide timely advice or assistance.

### 3.2 Deep System Integration
*   **Tool Usage:** Full access to system-level tools and CLI.
*   **App Orchestration:** Ability to open, close, and manipulate desktop applications.
*   **HID Control:** Programmatic movement of the mouse and keyboard input for UI automation.
*   **Scripting:** Capability to write and execute scripts (Python, Bash, JS) on the fly.

### 3.3 Skill Acquisition
*   **Claude Skills:** Integration with native Claude-based capabilities.
*   **Clawhub:** Integration with the Clawhub repository for community-driven or specialized AI skills.
*   **Dynamic Loading:** Friday can download and "learn" new skills during runtime to solve specific problems.

### 3.4 Self-Improvement
*   **Codebase Access:** Friday has read/write access to its own source code.
*   **Refactoring:** Can suggest or implement optimizations to its own logic, memory handling, or tool-use protocols.

### 3.5 Agent Orchestration
*   **Prime Agent:** Friday acts as the central orchestrator.
*   **Sub-Agents:** Can spawn and manage specialized agents for parallel processing (e.g., one agent researches while another writes code).

---

## 4. Technical Architecture

### 4.1 Speech & Latency Stack
*   **STT (Speech-to-Text):** Local Whisper (`base.en` model) for low-latency, private transcription.
*   **TTS (Text-to-Speech):** Edge TTS supporting streaming output bytes.
*   **Latency Optimization (Pipelining):**
    *   **Sentence-Level Streaming:** LLM output is split into sentences; each sentence is sent to TTS as soon as it's generated.
    *   **Hold-One-Ahead Pattern:** Used to flag `is_final` on the last segment without extra round-trips.
    *   **Client-Side Audio Queue:** Maintains a queue of pending audio segments for seamless, sequential playback using a "pump queue" logic.
    *   **VAD Tuning:** Voice Activity Detection window optimized to 0.8–1.0s to balance responsiveness and robustness.

### 4.2 Brain & Personality
*   **LLM Core:** Claude-based model for reasoning and tool use.
*   **Personality Management:**
    *   **LoRA:** Applied to the base model for core behavioral anchoring.
    *   **Recency Voice Cues:** Dynamic injection of personality-reinforcing prompts (one-liners, banned openers) into the *last user message* of every turn to prevent tonal drift.
    *   **Tonal Checkpoints:** Per-turn system prompt reinforcement ensuring length discipline and voice consistency.

### 4.3 UI Stack
*   **Frontend:** Vanilla HTML5, CSS3, and JavaScript (ES6+).
*   **Graphics:** Three.js via CDN for the 3D Cosmic Orb scene.
*   **Communication:** WebSockets or local API for real-time data transfer between the AI core and the UI.

---

## 5. Memory Architecture (Layered Model)

Friday’s memory is organized into distinct, specialized layers to mimic human-like cognitive processing and ensure long-term utility.

1.  **Sensory Layer (Ephemeral Buffer):**
    *   **Function:** Real-time stream processing of audio (Whisper) and system events.
    *   **Retention:** Seconds to minutes.
    *   **Purpose:** Identifying if a user is addressing Friday and detecting immediate environment changes.

2.  **Working Memory (Current Context):**
    *   **Function:** Holds the active conversation tree, current goal stack, and the state of any running sub-agents.
    *   **Retention:** Duration of the current task/session.
    *   **Purpose:** Maintaining coherence during complex, multi-step operations.

3.  **Narrative Memory (Short-Term):**
    *   **Function:** A rolling window of recent interactions, including summaries of past hours and the current day's events.
    *   **Retention:** 24–72 hours.
    *   **Purpose:** Providing immediate continuity ("As we discussed this morning...").

4.  **Semantic Memory (Long-Term/Vector):**
    *   **Function:** A Vector Database (ChromaDB/Pinecone) storing RAG-accessible data.
    *   **Contents:** User preferences, facts about the user's life, project histories, and recurring patterns.
    *   **Purpose:** Deep personalization and cross-session knowledge retrieval.

5.  **Procedural Memory (Skill/Tool Library):**
    *   **Function:** Stores the "How-To" for every tool (Claude Skills, Clawhub, custom scripts).
    *   **Contents:** API schemas, CLI commands, and successful execution patterns from previous attempts.
    *   **Purpose:** Improving tool-use reliability over time.

6.  **Episodic Memory (The "Log Book"):**
    *   **Function:** An immutable, chronological log of significant "life events" for the AI.
    *   **Contents:** Major milestones, self-improvement changes, and "ARG discoveries."
    *   **Purpose:** Creating a sense of shared history and "growth" between the user and Friday.

7.  **Architectural Memory (Self-Awareness):**
    *   **Function:** Direct mapping of its own codebase and system configuration.
    *   **Purpose:** Facilitating self-improvement and refactoring tasks.

---

## 6. System Requirements & Security

### 6.1 Requirements
*   **Compute:** High-performance GPU recommended for local Whisper and LoRA-enhanced inference.
*   **OS:** Windows/Linux/macOS with appropriate permissions for HID and system control.

### 6.2 Security & Safety
*   **Local Processing:** Whenever possible, process data locally (Whisper) to ensure privacy.
*   **Permission Tiers:** User-defined boundaries for mouse/keyboard control and file modification.
*   **Sandboxing:** Execution of unknown scripts in restricted environments where applicable.

---

## 7. Implementation Roadmap
1.  **Phase 1:** Basic UI (The Orb) + Whisper/Edge TTS integration.
2.  **Phase 2:** Tool use and system integration (App opening, HID control).
3.  **Phase 3:** Layered memory implementation and Vector DB setup.
4.  **Phase 4:** Proactive logic and autonomous "thought" cycles.
5.  **Phase 5:** Clawhub/Claude Skill integration and self-improvement modules.
6.  **Phase 6:** Multi-agent orchestration.
