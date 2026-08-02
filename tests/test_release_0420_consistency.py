from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.42.0"
BUILD = "gp-0420-20260802-1"
CONTRACT = "match-v6.1-page-worker"


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_worker_entry_uses_minimal_042_bootstrap():
    value = text("src/generic_parser/cloudflare_worker.py")
    assert "cloudflare_v042 import app" in value
    assert "cloudflare_v041 import app" not in value


def test_worker_identity_and_lazy_import_contract():
    value = text("src/generic_parser/cloudflare_v042.py")
    for token in (VERSION, BUILD, CONTRACT, "lazy_import_search_module", "page_worker_search"):
        assert token in value
    assert "from . import cloudflare_v039" not in value
    assert "importlib.import_module(SEARCH_MODULE)" in value


def test_browser_build_identity_is_consistent():
    index = text("cloudflare/public/index.html")
    controller = text("cloudflare/public/controller-0420.js")
    handshake = text("cloudflare/public/handshake-0420.js")
    for value in (index, controller, handshake):
        assert VERSION in value
        assert BUILD in value
    assert CONTRACT in controller
    assert CONTRACT in handshake


def test_pwa_cache_contains_only_042_runtime_assets():
    value = text("cloudflare/public/service-worker.js")
    assert "generic-parser-mobile-0.42.0-gp-0420-20260802-1" in value
    assert "controller-0420.js" in value
    assert "handshake-0420.js" in value
    assert "eventlog-0420.js" in value
    assert "handshake-0411.js" not in value


def test_eventlog_uses_042_storage():
    value = text("cloudflare/public/eventlog-0420.js")
    assert "generic-parser-eventlog-0420" in value
    assert BUILD in value
