import asyncio
import json
import re
import logging
from datetime import datetime
from core.brain import FridayBrain
from core.bridge import FridayBridge

logger = logging.getLogger("Friday.Proactive")


def extract_json(text):
    """Best-effort extraction of a JSON object from an LLM response that may be
    wrapped in markdown fences or surrounded by prose. Returns a dict or None."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start:end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None

class ProactiveEngine:
    """The 'Subconscious' of Friday. Periodically evaluates system state and chooses to act or speak."""

    def __init__(self, brain: FridayBrain):
        self.brain = brain
        self.bridge = FridayBridge()
        self.is_running = False
        self.last_thought_time = datetime.now()

    async def start(self, broadcast_callback):
        """Starts the proactivity loop."""
        self.is_running = True
        self.broadcast_callback = broadcast_callback
        while self.is_running:
            try:
                # Get interval from config
                with open("config/registry.json", "r") as f:
                    config = json.load(f)
                interval = config.get("system", {}).get("proactive_interval", 20) * 60

                await asyncio.sleep(interval)
                await self.run_cycle()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive Cycle Error: {e}")
                await asyncio.sleep(60)

    def stop(self):
        self.is_running = False

    async def run_cycle(self):
        """A single 'Thought -> Action' cycle."""
        logger.info("Friday is initiating a proactive thought cycle...")

        # 1. Gather Inputs
        vitals = self.bridge.get_system_vitals()
        tasks = self.brain.memory.layers.get("task", [])
        last_interaction = self.brain.memory.layers["episodic"][-1] if self.brain.memory.layers["episodic"] else None

        input_context = {
            "vitals": vitals,
            "current_tasks": tasks,
            "last_interaction": last_interaction,
            "time": datetime.now().strftime("%H:%M:%S")
        }

        # 2. Deliberation (Thought)
        # We ask the LLM if it wants to do something. We use a specific 'internal' prompt.
        thought_prompt = f"""
        Current System State: {json.dumps(input_context)}

        You are Friday's subconscious. Based on the state above, decide if you should:
        1. SPEAK: If there is something important to tell the user (vitals warning, task update, or just banter).
        2. ACT: Perform a system task (cleanup, optimization, or a quest-related action).
        3. SILENCE: If everything is fine and you shouldn't disturb the user.

        Respond in JSON format:
        {{
            "thought": "Your internal monologue here",
            "decision": "SPEAK" | "ACT" | "SILENCE",
            "payload": "The text to speak OR the tool to call",
            "tool_input": {{}} # If decision is ACT
        }}
        """

        try:
            # We use a non-streaming call for the internal thought
            if self.brain.provider == "anthropic":
                response = await self.brain.client.messages.create(
                    model=self.brain.config["ai_logic"]["llm_model"],
                    max_tokens=500,
                    system="You are the internal monologue of Friday, an advanced AI. Be proactive, observant, and slightly protective.",
                    messages=[{"role": "user", "content": thought_prompt}]
                )
                text = response.content[0].text
            else:
                response = await self.brain.client.chat.completions.create(
                    model=self.brain.config["ai_logic"]["llm_model"],
                    messages=[
                        {"role": "system", "content": "You are the internal monologue of Friday, an advanced AI. Be proactive, observant, and slightly protective."},
                        {"role": "user", "content": thought_prompt}
                    ],
                    max_tokens=500
                )
                text = response.choices[0].message.content

            decision_data = extract_json(text)
            if not decision_data or "decision" not in decision_data:
                logger.info("Proactive cycle: no actionable decision parsed; staying silent.")
                return

            thought = decision_data.get("thought", "")
            logger.info(f"Proactive Thought: {thought}")

            # Store thought in memory (Script layer or a new 'thought' layer)
            self.brain.memory.layers.setdefault("internal_monologue", []).append({
                "timestamp": datetime.now().isoformat(),
                "thought": thought
            })

            # 3. Output (Action or Speech)
            decision = decision_data.get("decision", "SILENCE")
            if decision == "SPEAK" and decision_data.get("payload"):
                await self.broadcast_callback(decision_data["payload"])
            elif decision == "ACT":
                tool_name = decision_data.get("payload")
                tool_input = decision_data.get("tool_input", {})
                if not tool_name:
                    logger.info("Proactive ACT decision had no tool payload; skipping.")
                    return
                result = await self.brain.execute_tool(tool_name, tool_input)
                logger.info(f"Proactive Action executed: {tool_name}. Result: {result}")

                # If the action resulted in something the user should know, speak it.
                if result and isinstance(result, str) and not result.startswith("PENDING"):
                     await self.broadcast_callback(f"Sir, I've taken the liberty of {tool_name}. {result}")

            self.brain.memory.save()

        except Exception as e:
            logger.error(f"Error in proactive deliberation: {e}")
