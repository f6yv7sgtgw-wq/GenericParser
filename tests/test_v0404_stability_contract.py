from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_worker_imports_direct_stable_page_worker():
    text = (ROOT / "src/generic_parser/cloudflare_v0404.py").read_text()
    assert "from . import cloudflare_v039 as page_worker" in text
    assert 'VERSION = "0.40.4"' in text


def test_production_entry_uses_v0404():
    text = (ROOT / "src/generic_parser/cloudflare_worker.py").read_text()
    assert "from generic_parser.cloudflare_v0404 import app" in text


def test_1101_guard_is_loaded_before_application():
    text = (ROOT / "cloudflare/public/index.html").read_text()
    guard = text.index("error-guard-0404.js")
    app = text.index("app.js?v=0.404")
    session = text.index("session-0403.js?v=0.404")
    assert guard < app < session


def test_1101_is_non_retryable():
    text = (ROOT / "cloudflare/public/error-guard-0404.js").read_text()
    assert "Worker threw exception" in text
    assert "retryable: false" in text
    assert "status: 422" in text


def test_pwa_cache_is_v0404():
    text = (ROOT / "cloudflare/public/service-worker.js").read_text()
    assert 'generic-parser-mobile-0.40.4' in text
    assert 'error-guard-0404.js?v=0.404' in text
