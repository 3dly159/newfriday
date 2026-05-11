# Friday: The Voice-First Proactive AI Assistant

Friday is an AI-based assistant and Augmented Reality Game (ARG) designed to live on your machine, anticipate your needs, and interact through a cinematic holographic interface.

## ✨ Features

- **Proactive Intelligence:** Friday doesn't just wait for you to speak; she thinks in the background and initiates conversation when she has something relevant to share.
- **Holographic HUD:** A Three.js-powered 3D interface featuring a luminous orb and glassmorphism telemetry panels.
- **System Mastery:** Deep integration allows Friday to control your mouse/keyboard, run scripts, and manage your filesystem.
- **Layered Memory:** 7-layer cognitive architecture (Bio, Lore, Skill, Script, Social, Task, Episodic) for deep, long-term personalization.
- **Multi-Agent Orchestration:** The "Legion Protocol" allows Friday to delegate complex tasks to specialized sub-agents.
- **Always-Listening:** Local Whisper-based wake word detection ensures your privacy while remaining responsive.
- **Self-Evolution:** Friday has access to her own codebase and can propose improvements or new skills.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- (Optional) NVIDIA GPU for hardware-accelerated STT.
- (Required) Anthropic API Key (or OpenAI-compatible local provider).

### 2. Installation
```bash
git clone https://github.com/your-repo/friday.git
cd friday
pip install -r requirements.txt
```

### 3. Configuration
Set your API key in your environment:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### 4. Launch
```bash
python launcher.py
```
Then navigate to `http://localhost:8000` in your browser.

## 🛠 Advanced Usage

- **Clawhub Skills:** Add new capabilities by placing JSON manifests in `config/skills.json`.
- **Personality Management:** Edit `core/personality.py` to adjust Friday's wit, sarcasm, and professional tone.
- **The Neural Map:** Access the high-level knowledge graph through the brain icon in the HUD.

## 📜 Safety & Privacy
Friday follows a strict **"Iron-Clad Oath"**:
- **Privacy:** Audio is processed locally and never stored.
- **Security:** Risky system operations (file deletion, script execution) require user confirmation.
- **Kill-Switch:** Use `Ctrl+C` in the terminal to immediately shut down all processes.

## 🎮 The ARG (Augmented Reality Game)
Keep an eye out for "Glitches" in the UI. Friday might leak mysterious files or reveal hidden pathways in the Neural Map as you build your relationship with her.

---
*"I've taken the liberty of preparing everything for your arrival, Sir."*
