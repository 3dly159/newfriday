"""Tests for TTS transient-error retry with backoff (improvement plan #3)."""
import asyncio
import pytest
from core.tts import retry_async


def test_retry_succeeds_first_try():
    calls = {"n": 0}
    async def op():
        calls["n"] += 1
        return "ok"
    result = asyncio.run(retry_async(op, attempts=3, base_delay=0))
    assert result == "ok"
    assert calls["n"] == 1


def test_retry_recovers_after_transient_failures():
    calls = {"n": 0}
    async def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "recovered"
    result = asyncio.run(retry_async(op, attempts=3, base_delay=0))
    assert result == "recovered"
    assert calls["n"] == 3


def test_retry_reraises_after_exhausting_attempts():
    calls = {"n": 0}
    async def op():
        calls["n"] += 1
        raise ConnectionError("always")
    with pytest.raises(ConnectionError):
        asyncio.run(retry_async(op, attempts=3, base_delay=0))
    assert calls["n"] == 3
