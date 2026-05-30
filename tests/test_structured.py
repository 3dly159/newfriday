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
