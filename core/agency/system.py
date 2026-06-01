import re
import subprocess
import platform as _platform

import psutil

# Catastrophic patterns refused regardless of permission (always on).
_DANGER_PATTERNS = [
    r"\brm\s+-rf?\s+(/|/\*|~|\$HOME)(\s|$)",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",   # fork bomb
    r"\bmkfs\b",
    r"\bdd\b.*\bof=/dev/",
    r">\s*/dev/(sd|nvme|hd)",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r"\brm\s+-rf?\s+--no-preserve-root",
]
_DANGER_RE = [re.compile(p) for p in _DANGER_PATTERNS]


def is_dangerous(cmd: str) -> bool:
    """True if the shell command matches a catastrophic pattern."""
    if not cmd:
        return False
    return any(rx.search(cmd) for rx in _DANGER_RE)


def volume_command(level: int) -> list:
    """Build a Linux amixer command to set master volume to `level` percent."""
    level = max(0, min(100, int(level)))
    return ["amixer", "-q", "sset", "Master", f"{level}%"]


def run_shell(cmd: str, timeout: int = 30) -> dict:
    """Run a shell command, refusing catastrophic ones. Returns stdout/stderr/exit_code."""
    if is_dangerous(cmd):
        return {"error": f"Refused dangerous command: {cmd}", "stdout": "", "exit_code": -1}
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except subprocess.TimeoutExpired as e:
        return {"error": "timed out", "stdout": e.stdout or "", "exit_code": -1}
    except Exception as e:
        return {"error": str(e), "stdout": "", "exit_code": -1}


def set_volume(level: int) -> str:
    try:
        subprocess.run(volume_command(level), capture_output=True, timeout=5)
        return f"Volume set to {max(0, min(100, int(level)))}%."
    except Exception as e:
        return f"Could not set volume: {e}"


def media_key(key: str) -> str:
    """Send a media key (play/pause/next/prev) via playerctl if present."""
    mapping = {"play": "play-pause", "pause": "play-pause", "next": "next", "prev": "previous"}
    action = mapping.get(key, key)
    try:
        subprocess.run(["playerctl", action], capture_output=True, timeout=5)
        return f"Media: {action}."
    except Exception as e:
        return f"Could not send media key: {e}"


def open_app(name: str) -> str:
    try:
        subprocess.Popen([name])
        return f"Opening {name}."
    except Exception as e:
        return f"Could not open {name}: {e}"


def close_app(name: str) -> str:
    try:
        result = subprocess.run(["pkill", "-f", name], capture_output=True, text=True, timeout=5)
        return f"Closed {name}." if result.returncode == 0 else f"No running process matched {name}."
    except Exception as e:
        return f"Could not close {name}: {e}"


def system_info() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
        "platform": _platform.system(),
        "release": _platform.release(),
    }
