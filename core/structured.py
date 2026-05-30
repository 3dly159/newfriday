import json
import re


def repair_json(text):
    """Best-effort extraction of a JSON object from LLM output that may be
    wrapped in markdown fences or surrounded by prose. Returns dict or None."""
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


_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_tool_args(tool_name, args, tools_schema):
    """Validate tool-call args against the tool's input_schema.

    Args:
        tool_name: name of the tool being called.
        args: dict of arguments produced by the model.
        tools_schema: the list of tool definitions (each with name/input_schema).

    Returns:
        (ok: bool, error: str). error is "" when ok.
    """
    schema = next((t for t in tools_schema if t.get("name") == tool_name), None)
    if schema is None:
        return False, f"Unknown tool: {tool_name}"
    if not isinstance(args, dict):
        return False, f"Arguments for {tool_name} must be an object, got {type(args).__name__}"

    input_schema = schema.get("input_schema", {})
    properties = input_schema.get("properties", {})

    for field in input_schema.get("required", []):
        if field not in args:
            return False, f"Missing required field '{field}' for {tool_name}"

    for field, value in args.items():
        spec = properties.get(field)
        if not spec:
            continue  # allow unspecified extras; only validate known props
        expected = spec.get("type")
        py_type = _TYPE_MAP.get(expected)
        # bool is a subclass of int; guard so booleans don't pass as integers
        if py_type and not isinstance(value, py_type):
            return False, f"Field '{field}' must be {expected}"
        if expected in ("integer", "number") and isinstance(value, bool):
            return False, f"Field '{field}' must be {expected}"
        if "enum" in spec and value not in spec["enum"]:
            return False, f"Field '{field}' must be one of {spec['enum']}"

    return True, ""
