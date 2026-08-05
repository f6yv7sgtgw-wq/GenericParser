from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from generic_parser.build_identity_v0450 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    VERSION,
)
from generic_parser.integrations import evercade_profile, snes_pal_profile
from generic_parser.module_api import (
    MODULE_CONTRACT,
    DebugTrace,
    ModuleDebugOptions,
    ModulePageRequest,
    ModuleSearchProfile,
    module_response_from_legacy,
    run_contract_self_tests,
)
from generic_parser.search_service_v0450 import validate_module_profile
from generic_parser import cloudflare_v0450 as module_worker
from generic_parser import search_service_v0450 as module_service

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_identity_and_reference() -> None:
    assert VERSION == "0.45.0"
    assert BUILD_ID == "gp-0450-20260805-1"
    assert API_CONTRACT == MODULE_CONTRACT == "generic-parser-module-v1"
    assert FUNCTIONAL_REFERENCE == "0.44.4"
    assert OPERATIONAL_REFERENCE == "0.44.6.5"


def test_profile_omits_empty_optional_rules() -> None:
    profile = ModuleSearchProfile(
        query="Evercade",
        required_terms=["Blaze", "", "blaze"],
        excluded_terms="",
        model_patterns=[],
        brands=None,
    )
    payload = profile.to_legacy_payload(page=4, source="auto")
    assert profile.required_terms == ["Blaze"]
    assert payload["required_terms"] == ["Blaze"]
    assert "excluded_terms" not in payload
    assert "model_patterns" not in payload
    assert "brands" not in payload
    assert "max_price" not in payload
    assert payload["page"] == 4

    validated = validate_module_profile(profile)
    assert validated["reference_request_validated"] is True
    assert "excluded_terms" not in validated["legacy_payload"]
    assert "model_patterns" not in validated["legacy_payload"]
    assert "brands" not in validated["legacy_payload"]


def test_location_requires_verified_location_id() -> None:
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", postal_code="53111")
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", radius_km=50)
    valid = ModuleSearchProfile(query="SNES", postal_code="53111", location_id=123, radius_km=50)
    assert valid.location_id == 123


def test_module_profile_matches_effective_reference_limits() -> None:
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="x")
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="x" * 121)
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", max_price=0)
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", market_value=0)
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", location_id=123, radius_km=201)


def test_debug_is_noop_by_default_and_opt_in_when_enabled() -> None:
    profile = ModuleSearchProfile(query="SNES")
    request = ModulePageRequest(profile=profile)
    legacy = {
        "listings": [],
        "pagination": {"next_page": None, "complete": True, "source": "fixture", "unique_listings": 0},
        "summary": {"fetched_listings": 0, "visible_listings": 0, "hidden_by_filter": 0},
    }
    disabled = module_response_from_legacy(
        legacy,
        request,
        DebugTrace(ModuleDebugOptions(), "disabled"),
    )
    assert disabled.debug is None

    debug_request = ModulePageRequest(profile=profile, debug=ModuleDebugOptions(enabled=True))
    enabled = module_response_from_legacy(
        legacy,
        debug_request,
        DebugTrace(debug_request.debug, "enabled"),
    )
    assert enabled.debug is not None
    assert enabled.debug.trace_id == "enabled"
    assert enabled.debug.payload is None


def test_module_result_contract_preserves_traffic_light() -> None:
    request = ModulePageRequest(profile=ModuleSearchProfile(profile_id="p1", query="SNES"), page=2)
    legacy = {
        "listings": [{
            "id": "42",
            "title": "SNES PAL",
            "url": "https://example.invalid/42",
            "price": 25,
            "postal_code": "53111",
            "place": "Bonn",
            "match": {"decision": "accept", "score": 100},
            "traffic_light": {"color": "green", "active_criteria": 2},
        }],
        "pagination": {"next_page": 3, "complete": False, "source": "fixture", "unique_listings": 1},
        "summary": {"fetched_listings": 1, "visible_listings": 1, "hidden_by_filter": 0, "reported_total": 10},
        "traffic_light_summary": {"green": 1, "yellow": 0, "red": 0},
        "deployment_identity": {"api_contract": MODULE_CONTRACT},
    }
    response = module_response_from_legacy(
        legacy,
        request,
        DebugTrace(ModuleDebugOptions(), "test"),
    )
    assert response.contract == MODULE_CONTRACT
    assert response.profile_id == "p1"
    assert response.listings[0].traffic_light["color"] == "green"
    assert response.pagination.next_page == 3
    assert response.summary.traffic_lights["green"] == 1


def test_network_free_self_test_and_project_adapters() -> None:
    result = run_contract_self_tests()
    assert result["ok"] is True
    assert result["network_used"] is False

    evercade = evercade_profile("Interplay Collection 1", market_value=30)
    assert evercade.query == "Evercade Interplay Collection 1"
    assert "Blaze" in evercade.brands

    snes = snes_pal_profile("Super Metroid", market_value=70)
    assert "PAL" in snes.required_terms
    assert "NTSC" in snes.excluded_terms


def test_worker_delegates_unchanged_reference_search() -> None:
    service = read("src/generic_parser/search_service_v0450.py")
    worker = read("src/generic_parser/cloudflare_worker.py")
    bootstrap = read("src/generic_parser/cloudflare_v0450.py")
    assert "from . import search_service_v0444 as reference" in service
    assert "result = await reference.search_page(payload, request)" in service
    assert "from generic_parser.cloudflare_v0450 import app" in worker
    assert '"packet_size": 7' in bootstrap
    assert '"pause_ms": 5000' in bootstrap
    assert '"enabled_by_default": False' in bootstrap
    assert '"network_used": False' in bootstrap
    assert '@app.post("/api/search")' in bootstrap
    assert '@app.post("/api/module/v1/search")' in bootstrap


def test_optional_app_token_protects_only_search_routes() -> None:
    def worker_request(token: str | None = None, *, protected: bool = True):
        headers = []
        if token is not None:
            headers.append((b"x-genericparser-token", token.encode("utf-8")))
        return module_worker.Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/module/v1/search",
                "raw_path": b"/api/module/v1/search",
                "query_string": b"",
                "headers": headers,
                "scheme": "https",
                "server": ("worker.example", 443),
                "client": ("127.0.0.1", 12345),
                "http_version": "1.1",
                "env": {"APP_TOKEN": "secret"} if protected else {},
            }
        )

    missing = module_worker._authenticate_search(worker_request())
    assert missing is not None
    assert missing.status_code == 401
    assert json.loads(missing.body)["phase"] == "authentication"
    assert missing.headers["x-genericparser-version"] == VERSION
    assert module_worker._authenticate_search(worker_request("wrong")) is not None
    assert module_worker._authenticate_search(worker_request("secret")) is None
    assert module_worker._authenticate_search(worker_request(protected=False)) is None


def test_browser_diagnostics_are_opt_in_and_fail_open() -> None:
    identity = read("cloudflare/public/build-identity-0450.js")
    controller = read("cloudflare/public/controller-0450.js")
    debug = read("cloudflare/public/module-debug-0450.js")
    index = read("cloudflare/public/index.html")
    assert "enabledByDefault:false" in identity
    assert "networkUsed:false" in identity
    assert "./controller-0411.js?v=0.450-reference-source" in controller
    assert "searchCoreChanged:false" in controller
    assert "debug-logs" in index and "module-tests" in index
    assert "module-debug-0450.js" in index
    assert "if (!I) return" in debug
    assert "Modultests sind deaktiviert" in debug
    assert "X-GenericParser-Debug" in debug


def test_version_metadata_marks_0450_module_release() -> None:
    metadata = json.loads(read("VERSION.json"))
    assert metadata["version"] == "0.45.0"
    assert metadata["build_id"] == "gp-0450-20260805-1"
    assert metadata["stable_reference_version"] == "0.44.6.5"
    assert metadata["module_contract"] == MODULE_CONTRACT
    assert metadata["debug_logging"]["enabled_by_default"] is False
    assert metadata["contract_tests"]["enabled_by_default"] is False


def test_module_http_contract_is_network_free_under_stubbed_reference(monkeypatch) -> None:
    async def fake_reference_search(payload, request):
        return {
            "listings": [
                {
                    "id": "live-contract-1",
                    "title": "Evercade Interplay Collection 1",
                    "url": "https://example.invalid/live-contract-1",
                    "price": 30,
                    "match": {"decision": "accept", "score": 100},
                    "traffic_light": {"color": "green"},
                }
            ],
            "pagination": {
                "next_page": 1,
                "complete": False,
                "source": "fixture",
                "unique_listings": 1,
            },
            "summary": {
                "fetched_listings": 1,
                "visible_listings": 1,
                "hidden_by_filter": 0,
                "reported_total": 10,
            },
            "traffic_light_summary": {"green": 1, "yellow": 0, "red": 0},
        }

    monkeypatch.setattr(module_worker, "_service", module_service)
    monkeypatch.setattr(module_service.reference, "search_page", fake_reference_search)
    client = TestClient(module_worker.app)

    health = client.get("/api/version")
    assert health.status_code == 200
    assert health.json()["module_contract"] == MODULE_CONTRACT
    assert health.headers["X-GenericParser-Build"] == BUILD_ID

    capabilities = client.get("/api/module/v1/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["sources"] == ["kleinanzeigen"]

    validated = client.post(
        "/api/module/v1/profile/validate",
        json={
            "profile_id": "http-contract",
            "query": "Evercade",
            "required_terms": [],
            "excluded_terms": [],
        },
    )
    assert validated.status_code == 200
    assert "required_terms" not in validated.json()["legacy_payload"]
    assert "excluded_terms" not in validated.json()["legacy_payload"]

    disabled = client.get("/api/module/v1/self-test")
    assert disabled.status_code == 409
    assert disabled.json()["tests_enabled"] is False
    enabled = client.get("/api/module/v1/self-test?enabled=true")
    assert enabled.status_code == 200
    assert enabled.json()["network_used"] is False

    searched = client.post(
        "/api/module/v1/search",
        headers={"X-GenericParser-Debug": "1"},
        json={
            "profile": {"profile_id": "http-contract", "query": "Evercade"},
            "page": 0,
            "source": "auto",
        },
    )
    assert searched.status_code == 200
    body = searched.json()
    assert body["contract"] == MODULE_CONTRACT
    assert body["profile_id"] == "http-contract"
    assert body["summary"]["visible"] == len(body["listings"]) == 1
    assert body["debug"]["enabled"] is True
    assert "payload" not in body["debug"]

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/api/module/v1/search" in openapi.json()["paths"]
