import asyncio
from core.agency import registry


class _FakePerms:
    def __init__(self, mapping): self._m = mapping
    def check(self, cat): return self._m.get(cat, "allow")


class _FakeBridge:
    def __init__(self, mapping): self.permissions = _FakePerms(mapping)


def test_every_tool_has_required_schema_fields():
    for tool in registry.AGENCY_TOOLS:
        assert "name" in tool and "description" in tool and "input_schema" in tool
        assert tool["name"] in registry.IMPL
        assert tool["name"] in registry.PERMISSION_MAP


def test_dispatch_denied_returns_message():
    bridge = _FakeBridge({"web_access": "deny"})
    out = asyncio.run(registry.dispatch("web_search", {"query": "x"}, bridge))
    assert isinstance(out, str) and "denied" in out.lower()


def test_dispatch_ask_returns_pending_sentinel():
    bridge = _FakeBridge({"shell": "ask"})
    out = asyncio.run(registry.dispatch("run_shell", {"cmd": "echo hi"}, bridge))
    assert out == "PENDING_APPROVAL: shell"


def test_dispatch_allow_runs_impl():
    bridge = _FakeBridge({"shell": "allow"})
    out = asyncio.run(registry.dispatch("run_shell", {"cmd": "echo hello-x"}, bridge))
    assert "hello-x" in out["stdout"]


def test_dispatch_unknown_tool():
    bridge = _FakeBridge({})
    out = asyncio.run(registry.dispatch("nope", {}, bridge))
    assert "unknown" in str(out).lower()
