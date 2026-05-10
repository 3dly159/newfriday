import os
import json
from anthropic import AsyncAnthropic
from core.personality import FridayPersonality
from core.bridge import FridayBridge
from core.memory import FridayMemory

class FridayBrain:
    def __init__(self):
        with open("config/registry.json", "r") as f:
            self.config = json.load(f)

        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.personality = FridayPersonality()
        self.bridge = FridayBridge()
        self.memory = FridayMemory()

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
            }
        ]

    async def get_streaming_response(self, user_input: str):
        # Update episodic memory
        self.memory.add_episodic("user", user_input)

        system_prompt = self.personality.get_system_prompt()
        # Inject memory context
        system_prompt += "\n\n" + self.memory.get_context_string()

        # Build message history from episodic memory
        messages = []
        for entry in self.memory.layers["episodic"]:
            messages.append({"role": entry["role"], "content": entry["content"]})

        async with self.client.messages.stream(
            model=self.config["ai_logic"]["llm_model"],
            max_tokens=self.config["ai_logic"]["max_tokens"],
            temperature=self.config["ai_logic"]["temperature"],
            system=system_prompt,
            messages=messages,
            tools=self.tools
        ) as stream:
            full_response = ""
            async for event in stream:
                if event.type == "text":
                    full_response += event.text
                    yield event.text

            # Save assistant response to memory
            if full_response:
                self.memory.add_episodic("assistant", full_response)

                # Handle tool use (simplified for the stream)
                if event.type == "tool_use":
                    # In a real implementation, we'd execute the tool and continue the conversation
                    # For now, we'll log it and yield a placeholder
                    tool_name = event.name
                    tool_input = event.input
                    result = await self.execute_tool(tool_name, tool_input)
                    # We would ideally send this back to Claude to get a final response
                    # yield f"\n[Executed {tool_name}: {result}]\n"

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
        return "Unknown tool"
