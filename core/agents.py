import os
import json
import asyncio
from anthropic import AsyncAnthropic

class FridayAgent:
    def __init__(self, name: str, role: str, system_prompt: str, model: str = "claude-3-5-sonnet-20241022"):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def execute_task(self, task: str):
        """Execute a specific task assigned by Prime."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=[{"role": "user", "content": task}]
        )
        return response.content[0].text

class ScoutAgent(FridayAgent):
    def __init__(self):
        prompt = """You are Scout, a specialized intelligence-gathering agent for the Friday AI system.
Your mission is to research, search, and gather information with extreme precision.
Provide concise, fact-based reports to Prime (Friday)."""
        super().__init__("Scout", "Intelligence", prompt)

class ArchitectAgent(FridayAgent):
    def __init__(self):
        prompt = """You are Architect, the codebase and system design specialist for Friday AI.
You excel at writing, refactoring, and documenting code.
You ensure the system remains scalable and efficient."""
        super().__init__("Architect", "Development", prompt)

class RelayAgent(FridayAgent):
    def __init__(self):
        prompt = """You are Relay, the communications specialist for Friday AI.
You handle external notifications, API integrations, and user alerts across multiple platforms.
Ensure all communications are clear and follow the established security protocols."""
        super().__init__("Relay", "Communications", prompt)

class LegionBroker:
    def __init__(self):
        self.agents = {
            "scout": ScoutAgent(),
            "architect": ArchitectAgent(),
            "relay": RelayAgent()
        }

    async def delegate(self, agent_name: str, task: str):
        if agent_name.lower() in self.agents:
            agent = self.agents[agent_name.lower()]
            print(f"[Legion] Delegating task to {agent.name}: {task[:50]}...")
            return await agent.execute_task(task)
        else:
            return f"Agent {agent_name} not found in the Legion Protocol."
