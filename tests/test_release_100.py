import json
from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser.cloudflare_v0452 import app
from generic_parser.cloudflare_v0450 import load_service
from generic_parser.release_identity import API_CONTRACT, BUILD_ID, VERSION

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_is_consistent() -> None:
    metadata = json.loads(read("VERSION.json"))
    package = read("pyproject.toml")
    identity = read("src/generic_parser/build_identity_v0452.py")
    assert metadata["version"] == VERSION
    assert metadata["build_id"] == BUILD_ID
    assert metadata["api_contract"] == API_CONTRACT
    assert metadata["identity_source"] == "src/generic_parser/release_identity.py"
    assert 'dynamic = ["version"]' in package
    assert 'generic_parser.release_identity.VERSION' in package
    assert "from .release_identity import" in identity


def test_public_browser_identity_is_runtime_loaded_not_release_pinned() -> None:
    browser = read("cloudflare/public/build-identity-0450.js")
    controller = read("cloudflare/public/controller-0450.js")
    assert "fetch('./health?identity=ui'" in browser
    assert "GP_BUILD_IDENTITY_READY" in browser
    assert "health.version" in browser
    assert "health.build_id" in browser
    assert "health.api_contract" in browser
    assert VERSION not in browser
    assert BUILD_ID not in browser
    assert "browser-run-worker+public-web-fallback" not in browser
    assert "vintedStrategy: 'service-binding'" in browser
    assert "GP_BUILD_IDENTITY_READY" in controller
    assert "workerContract !== API_CONTRACT" in controller
    assert "'if (workerVersion && workerContract !== API_CONTRACT) {'" in controller
    assert "Deployment inkonsistent: UI ${VERSION}/${BUILD_ID}" not in controller


def test_eventlog_uses_runtime_identity_without_release_pin() -> None:
    html = read("cloudflare/public/eventlog.html")
    script = read("cloudflare/public/eventlog-0450.js")
    assert "Log &amp; Diagnose" in html
    assert "data-version" in html
    assert "Build …" in html
    assert VERSION not in html
    assert BUILD_ID not in html
    assert "GP_BUILD_IDENTITY_READY" in script
    assert "document.title = `GenericParser Eventlog ${I.version}`" in script
    assert VERSION not in script
    assert BUILD_ID not in script
    assert "Service Binding + entkoppelte 3er-Detail-Batches" in script


def test_paid_timing_profile_is_active() -> None:
    browser = read("cloudflare/public/build-identity-0450.js")
    controller = read("cloudflare/public/controller-0450.js")
    assert "workerPlan: 'paid'" in browser
    assert "protectionDelays: false" in browser
    assert "quietPeriodMs: 1" in browser
    assert "healthIntervalMs: 1" in browser
    assert "COOLDOWN_MS = 0" in controller
    assert "adaptiveDelay = () => 0" in controller
    assert "countdown = async () => {}" in controller


def test_search_runtime_bridge_preserves_reference_identity() -> None:
    inner = read("src/generic_parser/build_identity_v0450.py")
    service = read("src/generic_parser/search_service_v0450.py")
    bridge = read("src/generic_parser/search_service_v111_runtime.py")
    assert 'VERSION = "0.45.0"' in inner
    assert 'SEARCH_MODULE = "generic_parser.search_service_v111_runtime"' in inner
    assert "from . import search_service_v0444 as reference" in service
    assert "from .vinted_adapter import search_vinted" in service
    assert "from .search_service_v0450 import" in bridge
    # 1.3 must not modify the protected orchestration service. Vinted detail
    # enrichment and multi-source display corrections live behind/in front of it.
    main_service = read("src/generic_parser/search_service_v0450.py")
    assert service == main_service
    controller = read("cloudflare/public/controller-0450.js")
    assert "detail_enrichment" in controller
    assert "reported_total" in controller
    loaded = load_service()
    assert loaded.VERSION == "0.45.0"
    assert loaded.API_CONTRACT == API_CONTRACT


def test_public_health_uses_single_release_identity() -> None:
    client = TestClient(app)
    headers = {"Origin": "https://f6yv7sgtgw-wq.github.io"}
    health = client.get("/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["version"] == VERSION
    assert health.json()["build_id"] == BUILD_ID
    assert health.headers["access-control-allow-origin"] == "*"
    version = client.get("/version", headers=headers)
    assert version.status_code == 200
    assert version.json()["version"] == VERSION
    assert version.json()["build_id"] == BUILD_ID
    capabilities = client.get("/api/module/v1/capabilities", headers=headers)
    assert capabilities.status_code == 200
    assert capabilities.json()["contract"] == API_CONTRACT


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
