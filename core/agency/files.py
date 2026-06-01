import os
import fnmatch

# Names/paths that are never readable regardless of permission.
_SENSITIVE = ("id_rsa", "id_ed25519", ".env", "shadow", "passwd", ".aws", ".ssh")


def is_safe_path(path: str) -> bool:
    """True if path is a relative, non-sensitive path that doesn't escape cwd."""
    if not path:
        return False
    if path.startswith("/") or path.startswith("~"):
        return False
    if ".." in path.split(os.sep):
        return False
    low = path.lower()
    return not any(s in low for s in _SENSITIVE)


def filter_matches(names, pattern):
    """Filter filenames by a glob pattern (e.g. '*.py')."""
    return [n for n in names if fnmatch.fnmatch(n, pattern)]


def truncate(text: str, max_chars: int) -> str:
    """Cap text length, appending a notice when cut."""
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[truncated]"


def read_file(path: str, max_chars: int = 8000) -> str:
    """Read a safe relative text file, truncated."""
    if not is_safe_path(path):
        return f"Refused: '{path}' is not an allowed path."
    try:
        with open(path, "r", errors="replace") as f:
            return truncate(f.read(), max_chars)
    except Exception as e:
        return f"Could not read {path}: {e}"


def list_dir(path: str = "."):
    """List entries of a safe directory (names only)."""
    if path not in (".", "") and not is_safe_path(path):
        return [f"Refused: '{path}' is not an allowed path."]
    try:
        return sorted(os.listdir(path or "."))
    except Exception as e:
        return [f"Could not list {path}: {e}"]


def search_files(root: str, pattern: str, max_results: int = 50):
    """Recursively find files matching a glob under a safe root."""
    if root not in (".", "") and not is_safe_path(root):
        return [f"Refused: '{root}' is not an allowed path."]
    found = []
    for dirpath, _dirs, names in os.walk(root or "."):
        for name in filter_matches(names, pattern):
            found.append(os.path.join(dirpath, name))
            if len(found) >= max_results:
                return found
    return found


def clipboard_get() -> str:
    """Return clipboard text, or an 'unavailable' note on headless/no-dep."""
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception as e:
        return f"Clipboard unavailable: {e}"


def clipboard_set(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Clipboard set."
    except Exception as e:
        return f"Clipboard unavailable: {e}"


def screenshot(out_path: str = "data/logs/screenshot.png") -> str:
    """Capture the screen to a file; degrade gracefully if headless."""
    try:
        import pyautogui
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        img = pyautogui.screenshot()
        img.save(out_path)
        return out_path
    except Exception as e:
        return f"Screenshot unavailable: {e}"
