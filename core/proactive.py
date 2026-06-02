import asyncio
import json
import logging
from datetime import datetime
from core.brain import FridayBrain
from core.bridge import FridayBridge
from core.structured import repair_json

logger = logging.getLogger("Friday.Proactive")


def extract_json(text):
    """Backwards-compatible alias; delegates to structured.repair_json."""
    return repair_json(text)

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
        """A single trigger-scan cycle: gather signals, score, and speak only if
        a candidate clears the balanced threshold."""
        from core.triggers import evaluate_triggers, THRESHOLD
        from core.presence import is_present
        logger.info("Friday proactive scan...")

        # User-set schedules fire regardless of camera presence.
        try:
            from core.scheduler import load_schedule, due_entries, save_schedule
            from datetime import datetime as _dt
            entries = load_schedule()
            due = due_entries(entries)
            for d in due:
                await self.broadcast_callback(d.get("text", "Reminder, Sir."))
                d["last_run"] = _dt.now().isoformat()
            # Remove fired one-offs; keep recurring.
            if due:
                kept = [e for e in entries if e.get("kind") == "recurring" or not e.get("last_run")]
                save_schedule(kept)
        except Exception as e:
            logger.error(f"Schedule check error: {e}")

        # SeelSupport: check for new notifications (work alerts fire regardless of presence).
        try:
            from core.agency.seelsupport import check_new_notifications
            new_notifs = check_new_notifications()
            for n in new_notifs:
                title = n.get("title", "Notification")
                msg = n.get("message", "")
                await self.broadcast_callback(f"Sir, new notification: {title}. {msg}")
        except Exception as e:
            logger.error(f"SeelSupport notification check error: {e}")

        # Camera gate: only speak when the user is recognized in front of the
        # camera. Strict — no fresh presence report means stay silent.
        if not is_present():
            logger.info("Proactive scan: user not present at camera; staying silent.")
            return

        try:
            vitals = self.bridge.get_system_vitals()
            # bridge vitals don't include 'plugged'; treat full battery as plugged.
            vitals.setdefault("plugged", vitals.get("battery", 100) >= 99)
            tasks = self.brain.memory.layers.get("task", [])
            episodic = self.brain.memory.layers.get("episodic", [])
            last_topic = None
            for entry in reversed(episodic):
                if entry.get("role") == "user":
                    last_topic = entry.get("content", "")[:60]
                    break

            ctx = {
                "vitals": vitals,
                "tasks": tasks,
                "hour": datetime.now().hour,
                "idle_seconds": 0,
                "minutes_since_interaction": 0,
                "last_topic": last_topic,
            }

            # Inject SeelSupport work counts for trigger scoring.
            try:
                from core.agency.seelsupport import seel_fetch
                seel_tasks = seel_fetch("tasks")
                seel_tickets = seel_fetch("tickets")
                if isinstance(seel_tasks, list):
                    ctx["seel_pending_tasks"] = sum(1 for t in seel_tasks if t.get("status") in ("pending", "in_progress"))
                if isinstance(seel_tickets, list):
                    ctx["seel_open_tickets"] = sum(1 for t in seel_tickets if t.get("status") == "open")
            except Exception:
                pass  # non-critical; triggers just won't include work_tasks
            candidates = evaluate_triggers(ctx)
            top = candidates[0] if candidates else None
            if not top or top["score"] < THRESHOLD:
                logger.info("Proactive scan: nothing worth surfacing.")
                return

            # Phrase the chosen trigger in-persona via the brain (short, single line).
            hint = top["message_hint"]
            try:
                prompt = (f"As Friday, say ONE short, in-character spoken line to the user about: "
                          f"{hint}. No preamble, just the line.")
                line = ""
                async for tok in self.brain.get_streaming_response(prompt):
                    if not tok.startswith("[System") and not tok.startswith("[Approval") and not tok.startswith("[Result"):
                        line += tok
                line = line.strip() or hint
            except Exception as e:
                logger.error(f"Proactive phrasing error: {e}")
                line = hint

            await self.broadcast_callback(line)
            self.brain.memory.layers.setdefault("internal_monologue", []).append({
                "timestamp": datetime.now().isoformat(), "thought": f"[{top['kind']}] {hint}"})
            self.brain.memory.save()

        except Exception as e:
            logger.error(f"Error in proactive cycle: {e}")
