import os
import json
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from core.personality import FridayPersonality
from core.bridge import FridayBridge
from core.memory import FridayMemory
from core.agents import LegionBroker
from core.quest import QuestEngine
from core.skills import ClawhubManager
from core.dataset import DatasetCapturer
from core.structured import repair_json, validate_tool_args
from core import persona

class FridayBrain:
    def __init__(self):
        with open("config/registry.json", "r") as f:
            self.config = json.load(f)

        self.provider = self.config["ai_logic"].get("model_provider", "anthropic")
        if self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif self.provider == "ollama":
            self.client = AsyncOpenAI(
                api_key="ollama",
                base_url=self.config["ai_logic"].get("base_url", "http://localhost:11434/v1")
            )
        else:
            # For Nemotron via NVIDIA NIM or OpenAI
            api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or "placeholder_for_tests"
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=self.config["ai_logic"].get("base_url")
            )

        self.personality = FridayPersonality()
        self.bridge = FridayBridge()
        self.memory = FridayMemory()
        self.legion = LegionBroker(self)
        self.quest = QuestEngine(self.memory)
        self.skills = ClawhubManager(self.memory)

        capture_enabled = self.config.get("system", {}).get("capture_dataset", False)
        self.capturer = DatasetCapturer(
            enabled=capture_enabled,
            persona_version=persona.PERSONA_VERSION,
        )

        # Tools definition for Claude 3.5 Sonnet
        self.tools = [
            {
                "name": "create_task",
                "description": "Create a new task in the management system.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Short name for the task."},
                        "description": {"type": "string", "description": "Detailed description."},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                        "deadline": {"type": "string", "description": "Optional deadline (ISO format)."}
                    },
                    "required": ["name", "description"]
                }
            },
            {
                "name": "update_task",
                "description": "Update an existing task status or priority.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "The ID of the task to update."},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "delete_task",
                "description": "Remove a task from the system.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "The ID of the task to delete."}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "install_skill",
                "description": "Install a new skill from Clawhub by its ID.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "The ID of the skill to install."},
                        "remote_url": {"type": "string", "description": "Optional URL to a remote clawhub manifest."}
                    },
                    "required": ["skill_id"]
                }
            },
            {
                "name": "set_mood",
                "description": "Adjust Friday's mood and emotional bias.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "mood": {"type": "string", "enum": ["neutral", "sarcastic", "protective", "banter"]}
                    },
                    "required": ["mood"]
                }
            },
            {
                "name": "persist_script",
                "description": "Save a successful script as a permanent skill for future use.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Friendly name for the skill."},
                        "description": {"type": "string", "description": "What the skill does."},
                        "code": {"type": "string", "description": "The code content."},
                        "language": {"type": "string", "enum": ["python", "bash"]}
                    },
                    "required": ["name", "description", "code", "language"]
                }
            },
            {
                "name": "get_system_vitals",
                "description": "Get current CPU, RAM, and Battery status.",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "move_mouse",
                "description": "Move the mouse cursor to specific coordinates.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"}
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "click",
                "description": "Click the mouse at current or specific coordinates.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "Optional X coordinate"},
                        "y": {"type": "integer", "description": "Optional Y coordinate"}
                    }
                }
            },
            {
                "name": "type_text",
                "description": "Type text on the keyboard.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text to type"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "open_app",
                "description": "Open a specific application by name.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Name of the application (e.g., 'Notepad', 'Safari', 'Terminal')"}
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "run_script",
                "description": "Execute a Python or Bash script. Use this for complex system tasks.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "The code to execute"},
                        "language": {"type": "string", "enum": ["python", "bash"]}
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "delegate_to_legion",
                "description": "Delegate a sub-task to a specialized agent (Scout, Architect, Relay).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "string", "enum": ["Scout", "Architect", "Relay"]},
                        "task": {"type": "string", "description": "The task for the agent to perform."}
                    },
                    "required": ["agent", "task"]
                }
            },
            {
                "name": "read_source",
                "description": "Read a source file from the codebase.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Relative path to the file."}
                    },
                    "required": ["filepath"]
                }
            },
            {
                "name": "write_source",
                "description": "Write or update a source file in the codebase. Always creates a backup by default.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Relative path to the file."},
                        "content": {"type": "string", "description": "The new content for the file."},
                        "backup": {"type": "boolean", "description": "Whether to create a .bak file first."}
                    },
                    "required": ["filepath", "content"]
                }
            },
            {
                "name": "run_tests",
                "description": "Run pytest on the codebase to verify changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Directory or file pattern to test."}
                    }
                }
            }
        ]

    async def get_streaming_response(self, user_input: str):
        # Update episodic memory
        self.memory.add_episodic("user", user_input)

        # Check Quest Progress
        quest_updates = self.quest.check_progress(user_input)

        system_prompt = self.personality.get_system_prompt()
        exemplar_block = persona.format_exemplars(
            persona.select_exemplars(user_input, limit=3)
        )
        if exemplar_block:
            system_prompt += "\n\n" + exemplar_block
        system_prompt += "\n\n" + self.skills.get_installed_skills_prompt()
        system_prompt += "\n\n" + self.memory.get_context_string(current_query=user_input)

        messages = []
        for entry in self.memory.layers["episodic"]:
            # Claude expects role and content, and tool use must follow assistant role
            messages.append({"role": entry["role"], "content": entry["content"]})

        final_text = ""
        try:
            if self.provider == "anthropic":
                # Initial request
                response = await self.client.messages.create(
                    model=self.config["ai_logic"]["llm_model"],
                    max_tokens=self.config["ai_logic"]["max_tokens"],
                    temperature=self.config["ai_logic"]["temperature"],
                    system=system_prompt,
                    messages=messages,
                    tools=self.tools
                )

                while response.stop_reason == "tool_use":
                    # Process tool calls
                    tool_calls = [block for block in response.content if block.type == "tool_use"]

                    # Update history with assistant's tool call
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for tool_call in tool_calls:
                        # Yield a notification to the UI about the tool being used
                        yield f"[System: Executing {tool_call.name}...]"
                        result = await self.execute_tool(tool_call.name, tool_call.input)
                        # Check quest progress on tool execution
                        quest_updates.extend(self.quest.check_progress(json.dumps(tool_call.input), tool_executed=tool_call.name))

                        marker = self._approval_marker(result)
                        if marker:
                            yield marker

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": json.dumps(result)
                        })

                    # Update history with tool results
                    messages.append({"role": "user", "content": tool_results})

                    # Get next response from Claude
                    response = await self.client.messages.create(
                        model=self.config["ai_logic"]["llm_model"],
                        max_tokens=self.config["ai_logic"]["max_tokens"],
                        temperature=self.config["ai_logic"]["temperature"],
                        system=system_prompt,
                        messages=messages,
                        tools=self.tools
                    )

                # Final text response
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                        yield block.text
            else:
                # OpenAI / Nemotron path
                # Convert tools to OpenAI format
                openai_tools = []
                for t in self.tools:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t["description"],
                            "parameters": t["input_schema"]
                        }
                    })

                # Nemotron doesn't always support the exact same message structure as Claude,
                # but usually follows OpenAI.
                response = await self.client.chat.completions.create(
                    model=self.config["ai_logic"]["llm_model"],
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    tools=openai_tools,
                    tool_choice="auto"
                )

                while response.choices[0].message.tool_calls:
                    tool_calls = response.choices[0].message.tool_calls

                    # Some OpenAI-compatible servers (notably Ollama) return tool
                    # calls with a missing/empty id. Synthesize a stable one so the
                    # assistant/tool message pairing doesn't raise KeyError: 'id'.
                    def _tc_id(tc, i):
                        return getattr(tc, "id", None) or f"call_{i}"

                    # Normalize assistant message
                    assistant_msg = {
                        "role": "assistant",
                        "content": response.choices[0].message.content or "",
                        "tool_calls": [
                            {
                                "id": _tc_id(tc, i),
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for i, tc in enumerate(tool_calls)
                        ]
                    }
                    messages.append(assistant_msg)

                    for i, tool_call in enumerate(tool_calls):
                        yield f"[System: Executing {tool_call.function.name}...]"
                        raw_args = tool_call.function.arguments
                        parsed_args = repair_json(raw_args)
                        if parsed_args is None:
                            try:
                                parsed_args = json.loads(raw_args)
                            except (json.JSONDecodeError, ValueError, TypeError):
                                parsed_args = {}

                        ok, err = validate_tool_args(
                            tool_call.function.name, parsed_args, self.tools
                        )
                        if not ok:
                            # Hand the model its own mistake so it can self-correct
                            # on the next turn, instead of executing garbage.
                            result = {"error": f"Invalid tool call: {err}"}
                        else:
                            result = await self.execute_tool(
                                tool_call.function.name, parsed_args
                            )

                        marker = self._approval_marker(result)
                        if marker:
                            yield marker

                        messages.append({
                            "role": "tool",
                            "tool_call_id": _tc_id(tool_call, i),
                            "name": tool_call.function.name,
                            "content": json.dumps(result)
                        })

                    response = await self.client.chat.completions.create(
                        model=self.config["ai_logic"]["llm_model"],
                        messages=[{"role": "system", "content": system_prompt}] + messages,
                        tools=openai_tools
                    )

                final_text = response.choices[0].message.content or ""
                if final_text:
                    yield final_text
        except Exception as e:
            # Respond in-character instead of failing silently. Distinguish a real
            # connection problem from an internal bug so we don't keep blaming
            # Ollama for our own errors (and so bugs stay debuggable).
            import traceback
            print(f"[Brain Error] {self.provider}: {type(e).__name__}: {e}")
            traceback.print_exc()
            fallback = self._error_message(e)
            self.memory.add_episodic("assistant", fallback)
            yield fallback
            return

        if final_text:
            self.memory.add_episodic("assistant", final_text)
            self.capturer.capture(
                system=system_prompt,
                user=user_input,
                reply=final_text,
                model=self.config["ai_logic"].get("llm_model", "unknown"),
            )

    async def execute_tool(self, name: str, input_data: dict):
        if name == "create_task":
            return self.memory.add_task(
                input_data.get("name"),
                input_data.get("description"),
                input_data.get("priority", "medium"),
                input_data.get("deadline")
            )
        elif name == "update_task":
            return self.memory.update_task(
                input_data.get("task_id"),
                input_data.get("status"),
                input_data.get("priority")
            )
        elif name == "delete_task":
            return self.memory.delete_task(input_data.get("task_id"))
        elif name == "install_skill":
            return self.skills.install_skill(input_data.get("skill_id"), input_data.get("remote_url"))
        elif name == "persist_script":
            return self.skills.persist_script_as_skill(
                input_data.get("name"),
                input_data.get("description"),
                input_data.get("code"),
                input_data.get("language")
            )
        elif name == "set_mood":
            return self.personality.set_mood(input_data.get("mood"))
        elif name == "get_system_vitals":
            return self.bridge.get_system_vitals()
        elif name == "move_mouse":
            return self.bridge.move_mouse(input_data.get("x"), input_data.get("y"))
        elif name == "click":
            return self.bridge.click(input_data.get("x"), input_data.get("y"))
        elif name == "type_text":
            return self.bridge.type_text(input_data.get("text"))
        elif name == "open_app":
            return self.bridge.open_app(input_data.get("app_name"))
        elif name == "run_script":
            return self.bridge.run_script(input_data.get("code"), input_data.get("language"))
        elif name == "delegate_to_legion":
            return await self.legion.delegate(input_data.get("agent"), input_data.get("task"))
        elif name == "read_source":
            return self.bridge.read_source(input_data.get("filepath"))
        elif name == "write_source":
            return self.bridge.write_source(input_data.get("filepath"), input_data.get("content"), input_data.get("backup", True))
        elif name == "run_tests":
            return self.bridge.run_tests(input_data.get("pattern", "tests/"))
        return "Unknown tool"

    def _approval_marker(self, result):
        """If a tool result is a pending-permission sentinel, return a marker
        token (caught by VoiceSession to raise the approval prompt). Else None."""
        if isinstance(result, str) and result.startswith("PENDING_APPROVAL:"):
            category = result.split(":", 1)[1].strip()
            return f"[Approval: {category}]"
        return None

    def _is_connection_error(self, error):
        """True only for genuine 'can't reach the brain' failures — not internal
        bugs like KeyError/TypeError, which must not be blamed on the server."""
        import httpx
        if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout,
                              httpx.ReadTimeout, ConnectionError, TimeoutError)):
            return True
        text = f"{type(error).__name__}: {error}".lower()
        markers = ("connection refused", "connect call failed", "cannot connect",
                   "failed to establish", "max retries", "timed out",
                   "name or service not known", "connection error", "apiconnectionerror")
        return any(m in text for m in markers)

    def _error_message(self, error):
        """In-character message. Connection failures get the 'start your brain'
        hint; everything else admits an internal hiccup honestly."""
        if self._is_connection_error(error):
            if self.provider == "ollama":
                hint = ("my local Ollama brain isn't responding. Start it with "
                        "'ollama serve' and make sure the model is pulled")
            elif self.provider == "anthropic":
                hint = "my Anthropic uplink is down. Do check that ANTHROPIC_API_KEY is set"
            else:
                hint = "my language core is unreachable"
            return f"My apologies, Sir — {hint}. I'll be quite useless until then."
        # Internal error — don't pretend the server is down.
        return ("My apologies, Sir — I hit an internal snag processing that "
                f"({type(error).__name__}). It's logged; do try again.")

    async def health_check(self):
        """Lightweight reachability probe for the configured provider."""
        info = {
            "provider": self.provider,
            "model": self.config["ai_logic"].get("llm_model"),
            "reachable": False,
            "detail": "",
        }
        try:
            if self.provider == "anthropic":
                has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
                info["reachable"] = has_key
                info["detail"] = "API key present" if has_key else "ANTHROPIC_API_KEY not set"
            else:
                import httpx
                base = (self.config["ai_logic"].get("base_url") or "").rstrip("/")
                if not base:
                    info["detail"] = "no base_url configured"
                    return info
                async with httpx.AsyncClient(timeout=3) as client:
                    resp = await client.get(f"{base}/models")
                    info["reachable"] = resp.status_code < 500
                    info["detail"] = f"HTTP {resp.status_code}"
        except Exception as e:
            info["detail"] = str(e)
        return info
