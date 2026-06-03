# Friday Codebase Improvement Plan

## 1. Replace Implicit Globals with Dependency Injection
- Identify modules that use module‑level globals (`config`, `logger`, `brain`).
- Refactor each class/function to accept these as constructor arguments.
- Update the startup routine to instantiate and pass the dependencies.
- Add unit tests confirming injected instances are used.

## 2. Add Comprehensive Type Hints
- Enable `mypy` in the project (`pyproject.toml` or `mypy.ini`).
- Annotate public APIs: `VoiceSession.run_turn`, FastAPI endpoint signatures, utility functions.
- Add a `py.typed` marker file.
- Run the type checker and fix any reported errors.

## 3. Robust Exception Handling & Retry Logic
- Wrap external service calls (LLM, STT, TTS) in try/except blocks.
- Implement exponential back‑off retry for transient network errors.
- Return structured error payloads to the UI instead of silent failures.

## 4. Structured Logging with Request IDs
- Switch from a single logger to a logger that includes a unique request ID (the UUID generated for each audio chunk).
- Use JSON‑formatted logs for easier ingestion by observability tools.
- Ensure all log statements include the request ID context.

## 5. Validate Config Updates
- Define a Pydantic model representing the allowed configuration schema.
- In the `/api/config` endpoint, parse incoming data against this model before writing to the file.
- Return validation errors to the client.

## 6. Add WebSocket Tests
- Mock `WebSocket` connections using `pytest‑asyncio` and `asgi‑testclient`.
- Feed simulated audio/text frames to verify wake‑word vs. addressed‑speech handling.
- Ensure coverage of the main message‑routing loop.

## 7. Documentation & Quick‑Start Guide
- Create a concise `README` section with:
  - VS Code extension list (React, React Native, C#, PHP, Python, SQL).
  - GitFlow branch naming conventions.
  - Steps to start the Ollama server, launch the FastAPI app, and open the UI.
- Add a Markdown cheat‑sheet (`QUICKSTART.md`) in the repo root.

## 8. Dependency Hygiene
- Migrate `requirements.txt` to a `pyproject.toml` managed by Poetry (or lock file).
- Pin exact versions to avoid breaking changes.
- Add a CI job that runs `poetry install --check`.

## 9. Improve UI Entry Point
- Refactor the root route to serve a single‑page application entry point that also delivers the manifest.
- Ensure static assets are correctly cached and served under `/ui`.
- Add a fallback route for unknown paths to return `index.html` (SPA routing support).

---
**Next Steps**
1. Commit this plan to the repository.
2. Create individual tickets for each improvement point (high priority where applicable).
3. Assign the tickets to the appropriate owner and set deadlines.
