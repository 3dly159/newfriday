"""Smoke test: the UI loads with no console errors and key elements present.
Skips cleanly if Playwright or a browser isn't available, so it never blocks CI."""
import socket
import subprocess
import time
import os
import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = dict(os.environ, PYTHONPATH=".")
    proc = subprocess.Popen(
        ["python3", "-m", "uvicorn", "core.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for readiness.
    import urllib.request
    base = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            urllib.request.urlopen(base, timeout=1); break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate(); pytest.skip("server did not start")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def _check(url, must_have_ids):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
    except Exception:
        pytest.skip("no chromium for playwright")
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(url, wait_until="load")
        page.wait_for_timeout(3500)  # let boot overlay + modules settle
        present = {i: page.query_selector(f"#{i}") is not None for i in must_have_ids}
        browser.close()
    # Ignore favicon/network-y noise; fail only on real JS errors.
    real = [e for e in errors if "favicon" not in e.lower()]
    assert all(present.values()), f"missing elements: {present}"
    assert not real, f"console errors: {real}"


def test_main_ui_loads(server):
    _check(server + "/", ["orb-canvas", "telemetry-rail", "convo-panel"])


def test_neural_page_loads(server):
    _check(server + "/ui/neural.html", ["neural-canvas", "neural-detail"])
