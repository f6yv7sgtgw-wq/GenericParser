from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_worker_entrypoint_uses_0408():
    text = (ROOT / "src/generic_parser/cloudflare_worker.py").read_text(encoding="utf-8")
    assert "cloudflare_v0408" in text


def test_0408_worker_uses_stable_page_worker():
    text = (ROOT / "src/generic_parser/cloudflare_v0408.py").read_text(encoding="utf-8")
    assert "cloudflare_v039" in text
    assert 'VERSION = "0.40.8"' in text


def test_0408_ui_loads_only_current_controller():
    text = (ROOT / "cloudflare/public/index.html").read_text(encoding="utf-8")
    assert "controller-0408.js" in text
    assert "controller-0407.js" not in text
    assert "session-0403.js" not in text
    assert "graceful-0406.js" not in text
    assert "diagnostic-0405.js" not in text


def test_0408_controller_logs_fetch_and_parse_boundaries():
    text = (ROOT / "cloudflare/public/controller-0408.js").read_text(encoding="utf-8")
    for marker in ("before_fetch", "after_fetch", "before_parse", "after_parse"):
        assert marker in text
    for field in ("requestId", "displayPage", "responseBytes", "contentType", "listingCount", "nextPage"):
        assert field in text


def test_0408_cache_assets_are_consistent():
    text = (ROOT / "cloudflare/public/service-worker.js").read_text(encoding="utf-8")
    assert "generic-parser-mobile-0.40.8" in text
    assert "controller-0408.js?v=0.408" in text
    assert "eventlog-0408.js?v=0.408" in text
