import os
import json
from anthropic import AsyncAnthropic
from core.personality import FridayPersonality
from core.bridge import FridayBridge
from core.memory import FridayMemory
from core.agents import LegionBroker

class FridayBrain:
    def __init__(self):
        with open("config/registry.json", "r") as f:
            self.config = json.load(f)

        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.personality = FridayPersonality()
        self.bridge = FridayBridge()
        self.memory = FridayMemory()
        self.legion = LegionBroker()

        # Tools definition for Claude 3.5 Sonnet
        self.tools = [
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

        system_prompt = self.personality.get_system_prompt()
        system_prompt += "\n\n" + self.memory.get_context_string(current_query=user_input)

        messages = []
        for entry in self.memory.layers["episodic"]:
            # Claude expects role and content, and tool use must follow assistant role
            messages.append({"role": entry["role"], "content": entry["content"]})

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

        if final_text:
            self.memory.add_episodic("assistant", final_text)

    async def execute_tool(self, name: str, input_data: dict):
        if name == "get_system_vitals":
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
