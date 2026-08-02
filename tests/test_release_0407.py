from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_worker_entry_uses_0407():
    text = (ROOT / "src/generic_parser/cloudflare_worker.py").read_text()
    assert "cloudflare_v0407" in text
    assert "cloudflare_v0406" not in text


def test_0407_worker_is_direct_and_has_no_diagnostic_chain():
    text = (ROOT / "src/generic_parser/cloudflare_v0407.py").read_text()
    assert "cloudflare_v039" in text
    assert "cloudflare_v0405" not in text
    assert "middleware" not in text
    assert "contextvars" not in text


def test_ui_loads_only_unified_controller():
    text = (ROOT / "cloudflare/public/index.html").read_text()
    assert "controller-0407.js" in text
    assert "session-0403.js" not in text
    assert "graceful-0406.js" not in text
    assert "diagnostic-0405.js" not in text


def test_controller_uses_graceful_stop_and_real_cooldown():
    text = (ROOT / "cloudflare/public/controller-0407.js").read_text()
    assert "stopRequested = true" in text
    assert "AbortController" not in text
    assert "await activeRun" in text
    assert "COOLDOWN_MS = 2000" in text
    assert "replaceButton('search-button')" in text
    assert "replaceButton('stop-button')" in text


def test_eventlog_is_throttled_and_bounded():
    text = (ROOT / "cloudflare/public/controller-0407.js").read_text()
    assert "MAX_LOG = 300" in text
    assert "last?.signature === signature" in text
    assert "workerState=function" not in text
