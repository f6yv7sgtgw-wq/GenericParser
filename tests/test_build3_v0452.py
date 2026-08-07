from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser.cloudflare_v0452 import app

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_build3_keeps_eager_0450_startup_model() -> None:
    worker = read("src/generic_parser/cloudflare_worker.py")
    wrapper = read("src/generic_parser/cloudflare_v0452.py")
    assert "from generic_parser.cloudflare_v0452 import app" in worker
    assert "from .cloudflare_v0450 import (" in wrapper
    assert "app.mount(\"/\", search_app)" in wrapper
    assert "lazy" not in worker.casefold()
    assert "importlib.import_module" not in wrapper


def test_build3_does_not_edit_search_service_runtime() -> None:
    service = read("src/generic_parser/search_service_v0450.py")
    assert "GenericParser 0.45 module service on the unchanged 0.44.4 search core" in service
    assert "from . import search_service_v0444 as reference" in service
    assert "from .build_identity_v0450 import" in service


def test_health_version_diagnostics_and_capabilities() -> None:
    client = TestClient(app)
    headers = {"Origin": "https://f6yv7sgtgw-wq.github.io"}

    health = client.get("/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["version"] == "0.45.2"
    assert health.json()["build_id"] == "gp-0452-20260807-3"
    assert health.json()["search_runtime"] == "0.45.0"
    assert health.headers["access-control-allow-origin"] == "*"

    version = client.get("/version", headers=headers)
    assert version.status_code == 200
    assert version.json()["build_id"] == "gp-0452-20260807-3"

    diagnostics = client.get("/diagnostics", headers=headers)
    assert diagnostics.status_code == 200
    assert diagnostics.json()["checks"]["startup_model"] == "eager-asgi-0450"

    capabilities = client.get("/api/module/v1/capabilities", headers=headers)
    assert capabilities.status_code == 200
    assert capabilities.json()["contract"] == "generic-parser-module-v1"
    assert capabilities.headers["access-control-allow-origin"] == "*"


def test_preflight_for_all_evercade_search_aliases() -> None:
    client = TestClient(app)
    headers = {
        "Origin": "https://f6yv7sgtgw-wq.github.io",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-genericparser-contract,x-request-id",
    }
    for path in ("/api/module/search", "/api/search", "/search"):
        response = client.options(path, headers=headers)
        assert response.status_code in (200, 204)
        assert response.headers["access-control-allow-origin"] == "*"
        assert "POST" in response.headers["access-control-allow-methods"]
