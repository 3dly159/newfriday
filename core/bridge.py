import os
import psutil
import subprocess
import platform

try:
    import pyautogui
    # Disable fail-safe for ARG "chaos" mode if desired, but keep it on for safety by default
    pyautogui.FAILSAFE = True
except (ImportError, Exception):
    # Many headless environments will throw errors on import (e.g. DISPLAY missing)
    pyautogui = None

class FridayBridge:
    """The 'Hands' of Friday. Controls HID and OS-level operations."""

    def __init__(self):
        self.system = platform.system()

    def get_system_vitals(self):
        """Returns CPU, RAM, and Battery status."""
        return {
            "cpu_usage": psutil.cpu_percent(interval=None),
            "memory_usage": psutil.virtual_memory().percent,
            "battery": psutil.sensors_battery().percent if psutil.sensors_battery() else 100,
            "temp": self._get_cpu_temp()
        }

    def _get_cpu_temp(self):
        # Implementation varies wildly by OS/Hardware, returning 0 as placeholder
        return 0

    def move_mouse(self, x: int, y: int):
        if pyautogui:
            pyautogui.moveTo(x, y, duration=0.5)
            return f"Moved mouse to {x}, {y}"
        return "Mouse control unavailable"

    def click(self, x: int = None, y: int = None):
        if pyautogui:
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return "Clicked"
        return "Click control unavailable"

    def type_text(self, text: str):
        if pyautogui:
            pyautogui.write(text, interval=0.1)
            return f"Typed: {text}"
        return "Keyboard control unavailable"

    def open_app(self, app_name: str):
        try:
            if self.system == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", app_name])
            elif self.system == "Windows":
                subprocess.Popen(["start", app_name], shell=True)
            else:  # Linux
                subprocess.Popen([app_name])
            return f"Opening {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}: {str(e)}"

    def run_script(self, code: str, language: str = "python"):
        """Executes a script and returns output. DANGEROUS - use with caution."""
        temp_file = f"data/temp_script.{'py' if language == 'python' else 'sh'}"
        with open(temp_file, "w") as f:
            f.write(code)

        try:
            if language == "python":
                result = subprocess.run(["python3", temp_file], capture_output=True, text=True, timeout=30)
            else:
                result = subprocess.run(["bash", temp_file], capture_output=True, text=True, timeout=30)

            os.remove(temp_file)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except Exception as e:
            if os.path.exists(temp_file): os.remove(temp_file)
            return {"error": str(e)}
