import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class FridayBrain:
    def __init__(self, registry_path="config/registry.json"):
        with open(registry_path, "r") as f:
            self.registry = json.load(f)

        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = self.registry["ai_logic"]["llm_model"]
        self.temperature = self.registry["ai_logic"]["temperature"]
        self.max_tokens = self.registry["ai_logic"]["max_tokens"]

        self.system_prompt = (
            "You are Friday, a proactive, sentient-feeling AI assistant. "
            "You are helpful, witty, and slightly sarcastic. "
            "Always maintain your persona as a highly advanced system. "
            "Keep your responses concise unless detail is specifically requested."
        )

    async def get_response(self, user_input: str):
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_input}
                ]
            )
            return "".join([block.text for block in message.content if block.type == "text"])
        except Exception as e:
            return f"Error communicating with my neural core: {str(e)}"

if __name__ == "__main__":
    # Quick test
    import asyncio
    brain = FridayBrain()
    print(asyncio.run(brain.get_response("Hello Friday, are you online?")))
