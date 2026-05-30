import os
from anthropic import AsyncAnthropic

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


class FridayAgent:
    """A specialized sub-agent. Reuses the Prime brain's provider/client so the
    Legion works under whatever backend Friday is configured for (Anthropic,
    Ollama, or any OpenAI-compatible endpoint)."""

    def __init__(self, name, role, system_prompt, provider="anthropic", client=None, model=None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.provider = provider
        self.model = model or DEFAULT_MODEL
        self.client = client
        if self.client is None:
            # Legacy fallback: stand up our own Anthropic client.
            self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.provider = "anthropic"

    async def execute_task(self, task: str):
        """Execute a specific task assigned by Prime."""
        try:
            if self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": task}],
                )
                return response.content[0].text
            else:
                # OpenAI-compatible (Ollama, OpenAI, NVIDIA NIM, ...)
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": task},
                    ],
                    max_tokens=1024,
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"[{self.name} is unavailable: {e}]"


class ScoutAgent(FridayAgent):
    def __init__(self, provider="anthropic", client=None, model=None):
        prompt = """You are Scout, a specialized intelligence-gathering agent for the Friday AI system.
Your mission is to research, search, and gather information with extreme precision.
Provide concise, fact-based reports to Prime (Friday)."""
        super().__init__("Scout", "Intelligence", prompt, provider, client, model)


class ArchitectAgent(FridayAgent):
    def __init__(self, provider="anthropic", client=None, model=None):
        prompt = """You are Architect, the codebase and system design specialist for Friday AI.
You excel at writing, refactoring, and documenting code.
You ensure the system remains scalable and efficient."""
        super().__init__("Architect", "Development", prompt, provider, client, model)


class RelayAgent(FridayAgent):
    def __init__(self, provider="anthropic", client=None, model=None):
        prompt = """You are Relay, the communications specialist for Friday AI.
You handle external notifications, API integrations, and user alerts across multiple platforms.
Ensure all communications are clear and follow the established security protocols."""
        super().__init__("Relay", "Communications", prompt, provider, client, model)


class LegionBroker:
    def __init__(self, brain=None):
        provider = getattr(brain, "provider", "anthropic")
        client = getattr(brain, "client", None)
        model = None
        if brain is not None:
            try:
                model = brain.config["ai_logic"]["llm_model"]
            except (KeyError, TypeError):
                model = None
        self.agents = {
            "scout": ScoutAgent(provider, client, model),
            "architect": ArchitectAgent(provider, client, model),
            "relay": RelayAgent(provider, client, model),
        }

    async def delegate(self, agent_name: str, task: str):
        if agent_name.lower() in self.agents:
            agent = self.agents[agent_name.lower()]
            print(f"[Legion] Delegating task to {agent.name}: {task[:50]}...")
            return await agent.execute_task(task)
        return f"Agent {agent_name} not found in the Legion Protocol."
