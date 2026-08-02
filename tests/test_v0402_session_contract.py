from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_session_controller_is_loaded_after_main_app() -> None:
    html = (ROOT / "cloudflare/public/index.html").read_text(encoding="utf-8")
    assert "app.js?v=0.402" in html
    assert "session-0402.js?v=0.402" in html
    assert html.index("app.js?v=0.402") < html.index("session-0402.js?v=0.402")


def test_session_controller_aborts_and_serializes_runs() -> None:
    script = (ROOT / "cloudflare/public/session-0402.js").read_text(encoding="utf-8")
    assert "AbortController" in script
    assert "await activeRun" in script
    assert "triggerOriginalStop" in script
    assert "activeController.abort" in script
    assert "state.sessionId" in script


def test_worker_and_ui_are_on_0402() -> None:
    worker = (ROOT / "src/generic_parser/cloudflare_worker.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "src/generic_parser/cloudflare_v0402.py").read_text(encoding="utf-8")
    html = (ROOT / "cloudflare/public/index.html").read_text(encoding="utf-8")
    service_worker = (ROOT / "cloudflare/public/service-worker.js").read_text(encoding="utf-8")
    assert "cloudflare_v0402" in worker
    assert 'VERSION = "0.40.2"' in wrapper
    assert "GenericParser 0.40.2" in html
    assert "generic-parser-mobile-0.40.2" in service_worker
