from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser.cloudflare_v0452 import app
from generic_parser.cloudflare_v0450 import load_service

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_is_consistent() -> None:
    metadata = read("VERSION.json")
    package = read("pyproject.toml")
    identity = read("src/generic_parser/build_identity_v0452.py")
    browser = read("cloudflare/public/build-identity-0450.js")
    assert '"version": "1.1.1"' in metadata
    assert '"build_id": "gp-111-20260808-1"' in metadata
    assert 'version = "1.1.1"' in package
    assert 'VERSION = "1.1.1"' in identity
    assert 'BUILD_ID = "gp-111-20260808-1"' in identity
    assert "version:'1.1.1'" in browser
    assert "buildId:'gp-111-20260808-1'" in browser


def test_paid_timing_profile_is_active() -> None:
    browser = read("cloudflare/public/build-identity-0450.js")
    controller = read("cloudflare/public/controller-0450.js")
    assert "workerPlan:'paid'" in browser
    assert "protectionDelays:false" in browser
    assert "quietPeriodMs:1" in browser
    assert "healthIntervalMs:1" in browser
    assert '["const COOLDOWN_MS = 2000;", "const COOLDOWN_MS = 0;"]' in controller
    assert "adaptiveDelay = () => 0" in controller
    assert "countdown = async () => {}" in controller


def test_search_runtime_bridge_preserves_reference_identity() -> None:
    outer = read("src/generic_parser/build_identity_v0452.py")
    inner = read("src/generic_parser/build_identity_v0450.py")
    service = read("src/generic_parser/search_service_v0450.py")
    bridge = read("src/generic_parser/search_service_v111_runtime.py")
    assert 'SEARCH_RUNTIME = "0.45.0+multisource-1.1-runtime-bridge"' in outer
    assert 'VERSION = "0.45.0"' in inner
    assert 'SEARCH_MODULE = "generic_parser.search_service_v111_runtime"' in inner
    assert "from . import search_service_v0444 as reference" in service
    assert "from .vinted_adapter import search_vinted" in service
    assert "from .search_service_v0450 import" in bridge
    loaded = load_service()
    assert loaded.VERSION == "0.45.0"
    assert loaded.BUILD_ID == "gp-0450-20260805-1"
    assert loaded.API_CONTRACT == "generic-parser-module-v1"


def test_health_version_diagnostics_and_capabilities() -> None:
    client = TestClient(app)
    headers = {"Origin": "https://f6yv7sgtgw-wq.github.io"}

    health = client.get("/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["version"] == "1.1.1"
    assert health.json()["build_id"] == "gp-111-20260808-1"
    assert health.headers["access-control-allow-origin"] == "*"

    version = client.get("/version", headers=headers)
    assert version.status_code == 200
    assert version.json()["version"] == "1.1.1"
    assert version.json()["build_id"] == "gp-111-20260808-1"

    diagnostics = client.get("/diagnostics", headers=headers)
    assert diagnostics.status_code == 200
    assert diagnostics.json()["checks"]["startup_model"] == "eager-asgi-0450"

    capabilities = client.get("/api/module/v1/capabilities", headers=headers)
    assert capabilities.status_code == 200
    assert capabilities.json()["contract"] == "generic-parser-module-v1"


def test_preflight_remains_browser_compatible() -> None:
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
