from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_location_requires_verified_location_id() -> None:
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", postal_code="53111")
    with pytest.raises(ValueError):
        ModuleSearchProfile(query="SNES", radius_km=50)
    valid = ModuleSearchProfile(query="SNES", postal_code="53111", location_id=123, radius_km=50)
    assert valid.location_id == 123


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
