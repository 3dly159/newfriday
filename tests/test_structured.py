from core.structured import repair_json


def test_repair_plain_json():
    assert repair_json('{"decision": "SPEAK"}') == {"decision": "SPEAK"}


def test_repair_fenced_json():
    text = 'Sure!\n```json\n{"decision": "ACT", "payload": "x"}\n```\nDone'
    assert repair_json(text)["payload"] == "x"


def test_repair_prose_wrapped_json():
    text = 'I think {"decision": "SILENCE"} is best.'
    assert repair_json(text)["decision"] == "SILENCE"


def test_repair_garbage_returns_none():
    assert repair_json("no json here") is None
    assert repair_json("") is None
    assert repair_json("{not valid json}") is None
    assert repair_json(None) is None


from core.structured import validate_tool_args

_SCHEMA = [
    {
        "name": "create_task",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "set_mood",
        "input_schema": {
            "type": "object",
            "properties": {"mood": {"type": "string", "enum": ["neutral", "banter"]}},
            "required": ["mood"],
        },
    },
]


def test_validate_accepts_good_args():
    ok, err = validate_tool_args("create_task", {"name": "x", "description": "y"}, _SCHEMA)
    assert ok is True
    assert err == ""


def test_validate_rejects_missing_required():
    ok, err = validate_tool_args("create_task", {"name": "x"}, _SCHEMA)
    assert ok is False
    assert "description" in err


def test_validate_rejects_bad_enum():
    ok, err = validate_tool_args("set_mood", {"mood": "furious"}, _SCHEMA)
    assert ok is False
    assert "mood" in err


def test_validate_rejects_wrong_type():
    ok, err = validate_tool_args("create_task", {"name": 5, "description": "y"}, _SCHEMA)
    assert ok is False
    assert "name" in err


def test_validate_unknown_tool():
    ok, err = validate_tool_args("nope", {}, _SCHEMA)
    assert ok is False
    assert "unknown" in err.lower()


def test_validate_non_dict_args():
    ok, err = validate_tool_args("set_mood", "neutral", _SCHEMA)
    assert ok is False
