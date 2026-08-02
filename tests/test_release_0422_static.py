from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.42.2"
BUILD = "gp-0422-20260802-1"
CONTRACT = "match-v6.1-page-worker"


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_worker_entry_uses_0422_only():
    value = text("src/generic_parser/cloudflare_worker.py")
    assert "cloudflare_v0422 import app" in value
    assert "cloudflare_v0421 import app" not in value


def test_service_is_app_free():
    value = text("src/generic_parser/search_service_v0422.py")
    assert "FastAPI(" not in value
    assert "@app." not in value
    assert "async def search_page" in value


def test_bootstrap_identity_and_consistency_gate():
    value = text("src/generic_parser/cloudflare_v0422.py")
    for token in (VERSION, BUILD, CONTRACT, "response_consistency", "app-free-one-page-service"):
        assert token in value
    assert "fetched == visible + hidden" in value
    assert "fetched == unique" in value
    assert "visible == len(listings)" in value


def test_public_assets_share_build_identity():
    files = [
        "cloudflare/public/index.html",
        "cloudflare/public/controller-0422.js",
        "cloudflare/public/handshake-0422.js",
        "cloudflare/public/eventlog.html",
        "cloudflare/public/eventlog-0422.js",
        "cloudflare/public/service-worker.js",
    ]
    for path in files:
        value = text(path)
        assert VERSION in value or "0.422" in value
        assert BUILD in value or path.endswith("service-worker.js")


def test_handshake_requires_app_free_service():
    value = text("cloudflare/public/handshake-0422.js")
    assert "includes('app-free')" in value
    assert "GP_CONTROLLER_VERSION!==UI_VERSION" in value
