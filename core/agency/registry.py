import inspect
from core.agency import web, files, system, documents


def _schedule_add(text, when):
    from core.scheduler import add_entry
    if not text or not when:
        return "Need both text and when (e.g. 'in 20m')."
    e = add_entry(text, when)
    return f"Scheduled ({e['id']}): \"{e['text']}\" — {e['when']}"


def _schedule_list():
    from core.scheduler import load_schedule
    entries = load_schedule()
    if not entries:
        return "No scheduled tasks."
    return [{"id": e["id"], "when": e["when"], "text": e["text"]} for e in entries]


def _schedule_cancel(entry_id):
    from core.scheduler import cancel_entry
    return f"Cancelled {entry_id}." if cancel_entry(entry_id) else f"No schedule with id {entry_id}."

# Tool schemas (same shape as core/brain.py tools).
AGENCY_TOOLS = [
    {"name": "web_search", "description": "Search the web for current information. Returns titles, URLs, snippets.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "fetch_page", "description": "Fetch a URL and return its readable text.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "read_file", "description": "Read a local text file (relative, non-sensitive path).",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "search_files", "description": "Find files matching a glob under a directory.",
     "input_schema": {"type": "object", "properties": {"root": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["root", "pattern"]}},
    {"name": "list_dir", "description": "List entries in a directory.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "clipboard_get", "description": "Read the system clipboard text.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "clipboard_set", "description": "Set the system clipboard text.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "screenshot", "description": "Capture the screen to an image file.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "close_app", "description": "Close/kill an application by name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "set_volume", "description": "Set system master volume (0-100).",
     "input_schema": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}},
    {"name": "media_key", "description": "Send a media key: play, pause, next, prev.",
     "input_schema": {"type": "object", "properties": {"key": {"type": "string", "enum": ["play", "pause", "next", "prev"]}}, "required": ["key"]}},
    {"name": "run_shell", "description": "Run a shell command (catastrophic commands are refused).",
     "input_schema": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}},
    {"name": "system_info", "description": "Get CPU, memory, and platform info.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "schedule_task", "description": "Schedule a reminder or recurring task. 'when' accepts 'in 20m', 'in 2h', 'at 17:00', or 'daily at 07:30'.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "when": {"type": "string"}}, "required": ["text", "when"]}},
    {"name": "list_schedules", "description": "List active reminders and scheduled tasks.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "cancel_schedule", "description": "Cancel a scheduled task by its id.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "read_document", "description": "Read a local document (text, markdown, or PDF) and return its text.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "search_in_document", "description": "Find lines matching a query inside a local document.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "query": {"type": "string"}}, "required": ["path", "query"]}},
]

# tool name -> permission category
PERMISSION_MAP = {
    "web_search": "web_access", "fetch_page": "web_access",
    "read_file": "file_read", "search_files": "file_read", "list_dir": "file_read",
    "clipboard_get": "clipboard", "clipboard_set": "clipboard",
    "screenshot": "screenshot",
    "close_app": "app_control",
    "set_volume": "app_control", "media_key": "app_control",
    "run_shell": "shell",
    "system_info": "file_read",
    "schedule_task": "schedule", "list_schedules": "schedule", "cancel_schedule": "schedule",
    "read_document": "documents", "search_in_document": "documents",
}

# tool name -> implementation callable
IMPL = {
    "web_search": lambda a: web.web_search(a.get("query", ""), a.get("max_results", 5)),
    "fetch_page": lambda a: web.fetch_page(a.get("url", ""), a.get("max_chars", 4000)),
    "read_file": lambda a: files.read_file(a.get("path", "")),
    "search_files": lambda a: files.search_files(a.get("root", "."), a.get("pattern", "*")),
    "list_dir": lambda a: files.list_dir(a.get("path", ".")),
    "clipboard_get": lambda a: files.clipboard_get(),
    "clipboard_set": lambda a: files.clipboard_set(a.get("text", "")),
    "screenshot": lambda a: files.screenshot(),
    "close_app": lambda a: system.close_app(a.get("name", "")),
    "set_volume": lambda a: system.set_volume(a.get("level", 50)),
    "media_key": lambda a: system.media_key(a.get("key", "play")),
    "run_shell": lambda a: system.run_shell(a.get("cmd", "")),
    "system_info": lambda a: system.system_info(),
    "schedule_task": lambda a: _schedule_add(a.get("text", ""), a.get("when", "")),
    "list_schedules": lambda a: _schedule_list(),
    "cancel_schedule": lambda a: _schedule_cancel(a.get("id", "")),
    "read_document": lambda a: documents.read_document(a.get("path", "")),
    "search_in_document": lambda a: documents.search_in_document(a.get("path", ""), a.get("query", "")),
}


def has_tool(name: str) -> bool:
    return name in IMPL


async def dispatch(name: str, args: dict, bridge):
    """Permission-gate and run an agency tool. Returns the impl result, or the
    existing PENDING_APPROVAL / denied sentinels used by the rest of the system."""
    if name not in IMPL:
        return f"Unknown agency tool: {name}"
    category = PERMISSION_MAP.get(name, "shell")
    perm = bridge.permissions.check(category)
    if perm == "deny":
        return f"Permission denied: {category}"
    if perm == "ask":
        return f"PENDING_APPROVAL: {category}"
    result = IMPL[name](args or {})
    if inspect.isawaitable(result):
        result = await result
    return result
