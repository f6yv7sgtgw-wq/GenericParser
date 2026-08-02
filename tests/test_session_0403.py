from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "cloudflare" / "public" / "index.html"
SESSION = ROOT / "cloudflare" / "public" / "session-0403.js"
WORKER = ROOT / "src" / "generic_parser" / "cloudflare_worker.py"
SW = ROOT / "cloudflare" / "public" / "service-worker.js"


def test_0403_assets_are_wired_consistently():
    index = INDEX.read_text(encoding="utf-8")
    worker = WORKER.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")
    assert "GenericParser 0.40.3" in index
    assert "session-0403.js?v=0.403" in index
    assert index.index("app.js?v=0.403") < index.index("session-0403.js?v=0.403")
    assert "cloudflare_v0403" in worker
    assert 'generic-parser-mobile-0.40.3' in sw
    assert 'session-0403.js?v=0.403' in sw


def test_session_controller_cancels_and_waits_before_new_search():
    source = SESSION.read_text(encoding="utf-8")
    assert "stopRequested = true" in source
    assert "activeController?.abort(reason)" in source
    assert "await activeRun" in source
    assert "await endActive('superseded')" in source
    assert "stopRequested = false" in source


def test_manual_stop_is_not_reported_as_retry_error():
    source = SESSION.read_text(encoding="utf-8")
    assert "Worker gestoppt" in source
    assert "wurde gestoppt" in source
    assert "undefined" not in source


def test_new_session_clears_old_results_before_start():
    source = SESSION.read_text(encoding="utf-8")
    assert "resetView()" in source
    assert "results').innerHTML = ''" in source
    assert "activeState = null" in source
