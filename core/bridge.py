import os
import json
import psutil
import subprocess
import platform

try:
    import pyautogui
    # Disable fail-safe for ARG "chaos" mode if desired, but keep it on for safety by default
    pyautogui.FAILSAFE = True
except (ImportError, Exception) as e:
    # Many headless environments will throw errors on import (e.g. DISPLAY missing or missing tkinter)
    pyautogui = None
    print(f"DEBUG: pyautogui could not be initialized: {e}")

class PermissionManager:
    def __init__(self, config_path="config/permissions.json"):
        self.config_path = config_path
        self.permissions = {
            "hid_control": "ask",      # options: allow, ask, deny
            "script_execution": "ask",
            "file_system_write": "ask",
            "app_orchestration": "allow"
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.permissions.update(json.load(f))

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.permissions, f, indent=4)

    def check(self, category):
        return self.permissions.get(category, "ask")

class FridayBridge:
    """The 'Hands' of Friday. Controls HID and OS-level operations."""

    def __init__(self):
        self.system = platform.system()
        self.permissions = PermissionManager()

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
        perm = self.permissions.check("hid_control")
        if perm == "deny": return "Permission denied: HID Control"
        if perm == "ask": return "PENDING_APPROVAL: hid_control"

        if pyautogui:
            pyautogui.moveTo(x, y, duration=0.5)
            return f"Moved mouse to {x}, {y}"
        return "Mouse control unavailable"

    def click(self, x: int = None, y: int = None):
        perm = self.permissions.check("hid_control")
        if perm == "deny": return "Permission denied: HID Control"
        if perm == "ask": return "PENDING_APPROVAL: hid_control"

        if pyautogui:
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return "Clicked"
        return "Click control unavailable"

    def type_text(self, text: str):
        perm = self.permissions.check("hid_control")
        if perm == "deny": return "Permission denied: HID Control"
        if perm == "ask": return "PENDING_APPROVAL: hid_control"

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
        perm = self.permissions.check("script_execution")
        if perm == "deny": return "Permission denied: Script Execution"
        if perm == "ask": return "PENDING_APPROVAL: script_execution"

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

    def read_source(self, filepath: str):
        """Read a source file from the codebase."""
        try:
            if ".." in filepath:
                return "Error: Path traversal not allowed."
            with open(filepath, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error: {e}"

    def write_source(self, filepath: str, content: str, backup: bool = True):
        """Write a source file, optionally creating a backup."""
        perm = self.permissions.check("file_system_write")
        if perm == "deny": return "Permission denied: File System Write"
        if perm == "ask": return "PENDING_APPROVAL: file_system_write"

        try:
            if ".." in filepath:
                return "Error: Path traversal not allowed."

            if backup and os.path.exists(filepath):
                import shutil
                shutil.copy2(filepath, f"{filepath}.bak")

            with open(filepath, "w") as f:
                f.write(content)
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error: {e}"

    def run_tests(self, pattern: str = "tests/"):
        """Run pytest on the specified pattern."""
        try:
            result = subprocess.run(["pytest", pattern], capture_output=True, text=True, timeout=60)
            return f"Test Results:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        except Exception as e:
            return f"Error running tests: {e}"
