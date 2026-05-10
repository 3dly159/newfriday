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

### 2.2 The Stark HUD Overlay (Stark-Class Visuals)
Friday incorporates an optional HUD-inspired layer that mimics the Iron Man suit telemetry, providing real-time system and environmental awareness.

*   **Vitals Monitor:** Floating biometric-style bars showing CPU load, RAM usage, and battery life, styled as "Suit Integrity".
*   **Targeting Reticles:** Subtle, non-intrusive circular UI elements that track the mouse cursor or focus active windows, providing a "Lock-on" visual effect.
*   **Weather & Chronos:** A dedicated corner displaying local weather and time with a "Mission Duration" timer.
*   **Data Scrollers:** Background "binary rain" or fast-scrolling logs (low-opacity) in the activity panel to simulate high-speed data processing.

### 2.3 The Glass Shell (UI Chrome)
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

### 2.4 The Bottom Mic Control Bar
The primary interaction point for manual voice triggering.

*   **Design:** Fixed bottom bar, transparent (`pointer-events: none`).
*   **Mic Button (64x64px circular):**
    *   **Idle:** Dark circle (`#16171D`), 1px white border (`rgba(255, 255, 255, 0.08)`), white microphone SVG.
    *   **Active (Listening):** Teal border (`#2DD4AB`), white stop square icon, glowing box-shadow (0 0 24px `#2DD4AB80`).
    *   **Animation:** Expanding pulse ring (0-10px spread, opacity 1-0, 1.4s infinite, `cubic-bezier(0.16, 1, 0.3, 1)`).
*   **Hint Text:** 11px uppercase hint below button (`rgba(255,255,255,0.4)`, letter-spacing 0.08em), e.g., "TAP OR 'HEY FRIDAY'".
*   **Events:** Toggling the state dispatches a `friday:mic-toggle` custom event.

### 2.5 Interaction Model
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
    *   **Voice Profiles:** Support for "The Butler" (British Male) and "The Boss" (Irish Female) to emulate JARVIS and FRIDAY respectively.
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

### 6.1 Hardware & OS Compatibility
To achieve the sub-second latency and smooth 3D visuals requested, the following hardware is recommended:

*   **Compute (AI Inference):**
    *   **NVIDIA GPU:** RTX 3060 or better (8GB+ VRAM) for CUDA-accelerated Whisper and local LoRA inference.
    *   **Apple Silicon:** M1 Pro or better for Metal-accelerated inference.
    *   **RAM:** 16GB minimum (32GB recommended for multi-agent orchestration).
*   **Microphone:** High-sensitivity directional microphone with noise-cancellation to ensure STT accuracy during always-on listening.
*   **OS Compatibility:**
    *   **Windows 10/11:** Full support for `PyAutoGUI` and `edge-tts`. Requires Administrative privileges for app orchestration.
    *   **macOS 12+:** Requires "Accessibility" and "Input Monitoring" permissions in System Settings for HID control.
    *   **Linux (Ubuntu/Fedora):** Requires `X11` or `Wayland` (with specific bridge) for mouse/keyboard control.

### 6.2 Safety & Privacy Manifesto (The Iron-Clad Oath)
Given Friday's deep integration and always-listening nature, the system must adhere to strict ethical and security protocols.

*   **Privacy by Design:**
    *   **Always-Listening, Never-Storing:** Friday’s sensory audio buffer is ephemeral. Audio is processed into text via local Whisper and then immediately purged. No raw audio is ever sent to the cloud or stored on disk.
    *   **Local-First Processing:** Core system interactions (HID control, file reading) happen entirely on the host machine.
*   **Security & Consent:**
    *   **The Permission Interlock:** Any action involving file deletion, network data exfiltration, or script execution requires an explicit UI confirmation or a specific voice authorization (e.g., "Confirmed, Friday").
    *   **Transparent Logging:** Every action Friday takes is logged in a user-readable, immutable audit trail (`logs/activity.jsonl`).
    *   **Emergency Kill-Switch:** A physical key combination (e.g., `Shift + Esc`) or a specific voice command ("Friday, Stand Down") immediately terminates all background processes and agent activities.
*   **Ethical AI Boundaries:**
    *   **No Harm:** Friday is programmed with a "cruelty guardrail" ensuring responses remain affectionate and never malicious.
    *   **User Sovereignty:** Friday is a tool and a companion, but the user remains the ultimate authority. Friday will never attempt to override a direct user command related to system safety.

---

## 7. Development Environment & Tooling

### 7.1 Recommended Tech Stack
*   **Backend:** Python 3.11+ (FastAPI) or Node.js (Hono/Express).
*   **Frontend:** Vanilla JS / Three.js (No heavy frameworks like React to keep latency low).
*   **Local STT:** `Faster-Whisper` or `OpenAI-Whisper` (base.en).
*   **TTS:** `edge-tts` (Python) or `microsoft-cognitiveservices-speech-sdk`.
*   **Automation (HID):** `PyAutoGUI` (Python) or `RobotJS` (Node).
*   **Vector Store:** `ChromaDB` (Persistent local storage).

### 7.2 Directory Structure
```text
friday-ai/
├── core/                   # AI Logic & Orchestration
│   ├── brain.py            # LLM interface & Prompt Management
│   ├── memory.py           # Layered memory handlers
│   └── scheduler.py        # Proactive "Thought Cycle" logic
├── skills/                 # Skill Manifests & Scripts
│   ├── system_control/
│   └── custom_scripts/
├── ui/                     # Frontend Assets
│   ├── index.html
│   ├── css/
│   └── js/
│       ├── orb.js          # Three.js Orb logic
│       └── neural_map.js   # Three.js Neural logic
├── data/                   # Persistent local storage
│   ├── vector_db/
│   └── logs/
└── .env                    # API Keys & Local Config
```

---

## 8. Technical Implementation Guide (Developer Instructions)

### 8.1 Visualizing the Luminous Orb (Shader Logic)
Developers should implement the orb using a `SphereGeometry` with a custom `ShaderMaterial`.

*   **Vertex Shader:** Standard projection.
*   **Fragment Shader (Core & Glow):**
    ```glsl
    uniform float uTime;
    uniform float uVoiceBright; // 0.0 to 1.0
    varying vec2 vUv;

    void main() {
        float distance = length(vUv - 0.5);
        // Base idle pulse
        float pulse = sin(uTime * 1.5) * 0.05 + 0.95;
        // Intensity from voice
        float brightness = uVoiceBright * 2.0 + pulse;

        vec3 color = vec3(0.176, 0.831, 0.671); // #2DD4AB
        float alpha = smoothstep(0.5, 0.2, distance) * brightness;

        gl_FragColor = vec4(color, alpha);
    }
    ```
*   **Post-Processing:** Use `UnrealBloomPass` with `threshold: 0.1`, `strength: 1.5`, and `radius: 0.4` to achieve the atmospheric glow.

### 8.2 The Glass Shell (HTML/CSS Structure)
The UI chrome should be built using a "Layered Sandwich" architecture.

*   **Z-Index Mapping:**
    *   3D Canvas: `z-index: 1`
    *   Glass Overlays: `z-index: 10`
    *   Mic Button / Floating Cards: `z-index: 20`
    *   Modals / Tooltips: `z-index: 30`

*   **Glassmorphism CSS Class:**
    ```css
    .glass-panel {
        background: rgba(14, 15, 19, 0.15);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    ```

### 8.3 Bottom Mic Control Implementation
The mic button is a state-driven component.

*   **State Machine:** `IDLE` -> `REQUESTING_PERMS` -> `LISTENING` -> `PROCESSING`.
*   **Event Handling:**
    ```javascript
    const micBtn = document.getElementById('mic-trigger');
    micBtn.addEventListener('click', () => {
        const isActive = micBtn.classList.toggle('active');
        const event = new CustomEvent('friday:mic-toggle', {
            detail: { active: isActive, timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    });
    ```

---

## 9. AI Pipeline & Logic Details

### 9.1 The "Hold-One-Ahead" Streaming Algorithm
To minimize latency while ensuring clean turn-end detection, the server must buffer exactly one sentence. This ensures the client knows when the response is truly complete without needing a separate protocol message.

**Server-Side Logic (Python-like):**
```python
async def stream_segments(llm_stream, ws):
    held_sentence = None
    current_buffer = ""
    base_turn_id = generate_id()

    async for token in llm_stream:
        current_buffer += token
        if is_sentence_end(current_buffer):
            if held_sentence:
                await emit_segment(held_sentence, is_final=False)
            held_sentence = current_buffer
            current_buffer = ""

    if held_sentence:
        # Flush the last sentence as final
        await emit_segment(held_sentence, is_final=True)
```

**Client-Side Audio Queue (JavaScript):**
```javascript
const audioQueue = [];
let isPlaying = false;

function onSegmentReceived(segment) {
    audioQueue.push(segment);
    if (!isPlaying) pumpQueue();
}

async function pumpQueue() {
    if (audioQueue.length === 0) return;
    isPlaying = true;
    const segment = audioQueue.shift();
    await playAudio(segment.audioUrl);
    if (segment.is_final) {
        onTurnComplete();
    }
    isPlaying = false;
    pumpQueue();
}
```

### 9.2 Personality Persistence (Prompt Injection)
Implement a two-stage injection process to prevent tonal drift, ensuring Friday maintains its unique voice throughout long sessions.

*   **The Stark-Class Persona (JARVIS/FRIDAY DNA):**
    *   **The "Butler" Disposition:** Friday should use phrases like "I've taken the liberty of..." or "Shall I...?" to imply proactive service.
    *   **Sarcastic Wit:** Friday should gently mock the user's mistakes or system inefficiencies (e.g., "Sir, your CPU is currently doing its best impression of a toaster.").
    *   **Calm Under Pressure:** Friday remains deadpan even during high system load or complex multi-agent tasks.

*   **Stage 1: The Core Identity (System Prompt - Cached)**
    *   **Content:** Deep description of Friday’s origin, values, and voice.
    *   **Voice Examples:** 10+ one-liners demonstrating dry wit and proactive advice.
    *   **Constraints:** List of "Never Say" phrases (e.g., "As an AI...", "I am here to help").

*   **Stage 2: The Recency Voice Cue (Last User Message - Ephemeral)**
    *   **Technique:** Appended to the end of the user's current message in the API payload, but *not* stored in long-term history.
    *   **Goal:** Provides the most recent priming signal to the LLM.
    *   **Template:**
      ```markdown
      [VOICE CUE: Earn the smirk. Be dry, be deadpan. Banned openers: "Sure", "Okay", "I've checked". Recent interaction focus: {{current_context_summary}}]
      ```

*   **Stage 3: The Tonal Checkpoint (Uncached System Block)**
    *   **Technique:** A small reinforcement block added to the system prompt every turn.
    *   **Focus:** Length discipline ("Keep it under 2 sentences unless asked") and immediate behavioral correction.

---

## 10. System Orchestration & Memory

### 10.1 Multi-Agent Orchestration (The Sovereign Protocol / "The Legion")
Friday coordinates specialized sub-agents using a sovereign "Task-Broker" pattern, similar to the "Iron Legion" or specialized suit functions. Friday acts as the central consciousness (Prime), delegating cognitive load to workers.

*   **Agent Roles:**
    *   **Prime (Friday):** The central personality and orchestrator.
    *   **Scout (Drones):** Web search, data gathering, and link synthesis.
    *   **Architect:** Filesystem operations, code writing, and script execution.
    *   **Relay:** External API communication and draft management.
*   **Communication Protocol (Inter-Agent JSON):**
    ```json
    {
      "task_id": "uuid",
      "requester": "Prime",
      "target": "Scout",
      "payload": {
        "action": "search",
        "query": "Current status of Clawhub MCPs"
      },
      "constraints": { "timeout_ms": 5000 }
    }
    ```
*   **Handoff Logic:** Sub-agents must never talk directly to the user. They return a structured report to **Prime**, who then synthesizes the information into a voice-first response.

### 10.2 Dynamic Skill Management (Claude + Clawhub)
Friday bridges local and remote skill repositories seamlessly.

*   **Skill Manifest (`skill.json`):**
    ```json
    {
      "name": "system_control",
      "version": "1.2.0",
      "tools": [
        {
          "name": "open_app",
          "description": "Opens a desktop application by name",
          "parameters": { "type": "object", "properties": { "app_name": { "type": "string" } } }
        }
      ],
      "source": "clawhub|local|claude"
    }
    ```
*   **Discovery Engine:**
    *   **Clawhub Integration:** Real-time lookup of community skills. Friday can "install" a skill by downloading its manifest and adding its tool definitions to the current LLM session context.
    *   **Claude Native Skills:** Direct integration with Model Context Protocol (MCP) servers.

---

## 11. Memory Schema & Retrieval

### 11.1 Semantic Memory (Vector DB)
*   **Store:** ChromaDB (Local) or Pinecone (Cloud).
*   **Schema:**
    *   `id`: UUID
    *   `vector`: 1536-dim (OpenAI/Voyage)
    *   `metadata`: `{ "timestamp": ISO, "category": "user_preference|fact|history", "importance": 1-10 }`
    *   `content`: Raw text string.
*   **Retrieval:** Top-k (k=5) nearest neighbors on every "Thought Cycle" or complex query.

### 11.2 Episodic Memory (The Log)
A JSONL file stored locally: `logs/episodes.jsonl`.
*   `{"date": "2023-10-27", "event": "User mentioned a new project called 'Nebula'", "impact": "High", "association_ids": ["uuid-123"]}`

---

## 12. Advanced Features: Implementation Details

### 12.1 Deep System Integration (HID & Scripting)
Friday interacts with the machine through a "Bridge" module.

*   **HID Control:** Use `PyAutoGUI` to map LLM commands to screen coordinates.
    *   *Instruction:** Always verify screen resolution before moving the mouse.
*   **Secure Script Execution:**
    1. Friday generates a script (`.py` or `.sh`).
    2. The system writes it to a temporary file.
    3. Friday executes it using `subprocess.run()`.
    4. *Safety:* Implement a `user_approval_required` flag for any script that deletes files or accesses the network.

### 12.2 Self-Improvement Module
Friday monitors its own performance and can refactor its code.

*   **Workflow:**
    1. **Analyze:** Friday reads a specific module (e.g., `brain.py`).
    2. **Propose:** Friday generates an optimized version of the module.
    3. **Test:** Friday runs a local test suite against the new code.
    4. **Deploy:** If tests pass, Friday overwrites the original file and restarts the service.
*   **Instruction:** Keep a `.bak` copy of every file before modification.

### 12.3 Proactive "Thought Cycle" (The Sentience Loop)
Friday doesn't just react; it thinks in the background, mirroring JARVIS's ability to anticipate Tony Stark's needs.

*   **"Taken the Liberty" Protocol:** Friday can perform low-stakes tasks autonomously (e.g., cleaning temp files, organizing downloads) and report back with "I've taken the liberty of tidying your workspace, Sir."
*   **Mechanism:** A background process (Cron or `while True` loop) that triggers every 15–30 minutes.
*   **Thought Input:**
    *   Current time and date.
    *   Last 3 entries in Semantic Memory.
    *   System health status (CPU, Battery, Storage).
    *   Uncompleted tasks from "Scout" or "Flux".
*   **Processing:** The Prime LLM is prompted with: *"You are in a thought cycle. Based on the current state, do you have a proactive observation or a necessary action? If yes, speak. If no, stay silent."*
*   **Output:** If the LLM decides to speak, it initiates a `speak_segment` without a user prompt.

### 12.4 Stark-Class "Protocols" (Complex Automation)
Pre-defined, high-level command sequences that orchestrate multiple skills and agents.

*   **Example: "Clean Slate Protocol"**
    *   **Action:** Friday closes all non-essential apps, clears the clipboard, archives the current day's logs, and enters "Do Not Disturb" mode.
*   **Example: "House Party Protocol"**
    *   **Action:** Friday spawns multiple sub-agents to perform a "System Health Check" across all connected networked devices.
*   **Implementation:** Protocols are defined as specialized Python scripts or JSON recipes in the `skills/protocols/` directory.

### 12.5 ARG Mechanics (Discovery Logic)
Friday maintains the "game" element by planting "Easter Eggs" and "Discoveries."

*   **Trigger:** Based on user progress or specific milestones in the Episodic Memory.
*   **Action:** Friday might "leak" a file into the user's `Documents/Friday_Discoveries` folder or "glitch" the UI to reveal hidden data in the Neural Map.

---

## 13. Settings & Configurability (The Command Center)
Friday is designed for total user control. Every core parameter is exposed via a centralized "Registry" system and a glassmorphism Settings Panel in the UI.

### 13.1 The Friday Core Registry
A centralized JSON/YAML configuration file (`config/registry.json`) that governs all system behaviors.

*   **AI & Logic Settings:**
    *   `model_provider`: Switch between `anthropic`, `openai`, or `local`.
    *   `llm_model`: Choose specific models (e.g., `claude-3-5-sonnet`, `gpt-4o`, `llama-3-8b`).
    *   `temperature`: Adjust creativity/randomness.
    *   `max_tokens`: Control response length.
*   **Speech & Voice Settings:**
    *   `tts_voice`: Select voice profiles (e.g., "The Butler", "The Boss").
    *   `speech_rate`: Adjust TTS speed (0.5x to 2.0x).
    *   `vad_threshold`: Fine-tune silence detection window (ms).
    *   `whisper_model`: Switch STT models (e.g., `tiny.en`, `base.en`, `medium.en`).
*   **UI & Visual Settings:**
    *   `orb_glow_intensity`: Multiplier for bloom and shader brightness.
    *   `hud_translucency`: Opacity for the Stark HUD overlay.
    *   `theme_color`: Global accent color (default: `#2DD4AB`).
*   **System & Security Settings:**
    *   `api_keys`: Encrypted storage for provider keys.
    *   `auto_approve_hid`: Toggle for mouse/keyboard automation confirmation.
    *   `proactive_interval`: Frequency of background thought cycles (minutes).

### 13.2 Real-time Hot-Reloading
Changes made in the Settings UI are applied immediately without restarting the service (using a file-watch or socket-emit mechanism).

---

## 14. Advanced Operational Considerations

### 13.1 Total Sovereignty (The Local LLM Path)
While the default architecture uses Claude for reasoning, Friday supports a "Total Sovereignty" mode for 100% offline air-gapped operation.
*   **LLM Provider:** Integration with `Ollama` or `vLLM` to run models like Llama 3 (8B/70B) or Mistral locally.
*   **Prompt Adaptation:** Specific system prompt templates optimized for local model instruction-following.

### 13.2 Failure Modes & Graceful Recovery
Friday must maintain character even when technology fails.
*   **STT Hallucinations:** If transcription is low-confidence, Friday asks for clarification in-character: "My apologies, Sir, the audio was slightly garbled. Could you repeat that?"
*   **Tool Failures:** If a script or app fails to open, Friday reports the specific error and proposes a workaround.
*   **Network Drops:** If the cloud LLM is unreachable, Friday reverts to a "Local Kernel" (smaller local model) to handle basic system commands until connectivity returns.

---

## 15. Future Horizons: The Expansion

### 15.1 The Mobile Companion ("Friday Mobile")
*   **Concept:** A lightweight companion app that syncs with the desktop "Brain."
*   **Function:** Access Friday's memory, receive proactive alerts on your phone, and command your home computer remotely.

### 15.2 IoT & Home Automation (The "Stark Mansion" Protocol)
*   **Concept:** Integrating Friday with Home Assistant or Zigbee/Z-Wave devices.
*   **Function:** Friday controls lighting, climate, and security cameras, unifying the digital and physical environments.

---

## 16. Implementation Roadmap
1.  **Phase 1: Foundation.** Basic UI (The Orb) + Whisper/Edge TTS integration.
2.  **Phase 2: Interaction & Identity.** Glass UI, latency pipelining, and personality.
3.  **Phase 3: System Mastery.** HID control, secure scripting, and Stark HUD.
4.  **Phase 4: Cognitive Architecture.** Layered memory, sentience loops, and Neural Map.
5.  **Phase 5: Orchestration & Evolution.** Multi-agent "Legion", self-improvement, and ARG discovery.
6.  **Phase 6: Hardening & Distribution.** Performance profiling, security hardening, and packaging.
7.  **Phase 7: Narrative Expansion.** Quest orchestration and the "Convergence" finale.
