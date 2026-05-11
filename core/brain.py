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
        self.legion = LegionBroker()
        self.quest = QuestEngine(self.memory)
        self.skills = ClawhubManager(self.memory)

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
        system_prompt += "\n\n" + self.skills.get_installed_skills_prompt()
        system_prompt += "\n\n" + self.memory.get_context_string(current_query=user_input)

        messages = []
        for entry in self.memory.layers["episodic"]:
            # Claude expects role and content, and tool use must follow assistant role
            messages.append({"role": entry["role"], "content": entry["content"]})

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
                    result = await self.execute_tool(tool_call.name, tool_call.input)
                    # Check quest progress on tool execution
                    quest_updates.extend(self.quest.check_progress(json.dumps(tool_call.input), tool_executed=tool_call.name))

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                    # Yield a notification to the UI about the tool being used
                    yield f"[System: Executing {tool_call.name}...]"

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
            final_text = ""
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
                messages.append(response.choices[0].message)

                for tool_call in tool_calls:
                    result = await self.execute_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(result)
                    })
                    yield f"[System: Executing {tool_call.function.name}...]"

                response = await self.client.chat.completions.create(
                    model=self.config["ai_logic"]["llm_model"],
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    tools=openai_tools
                )

            final_text = response.choices[0].message.content
            if final_text:
                yield final_text

        if final_text:
            self.memory.add_episodic("assistant", final_text)

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
