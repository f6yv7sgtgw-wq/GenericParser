"""GenericParser 0.45 module service on the unchanged 0.44.4 search core."""
from __future__ import annotations

from typing import Any

from fastapi import Request

from . import search_service_v0444 as reference
from .build_identity_v0450 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    VERSION,
    WORKER_UNIT,
)
from .integrations import evercade_profile, snes_pal_profile
from .module_api import (
    MODULE_CONTRACT,
    DebugTrace,
    ModulePageRequest,
    ModulePageResponse,
    ModuleSearchProfile,
    module_response_from_legacy,
    run_contract_self_tests,
)

SearchRequest = reference.SearchRequest


def identity() -> dict[str, Any]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "module_contract": MODULE_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "search_behavior_changed": False,
    }


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    """Kompatibilitätsroute für die unveränderte 0.44.6.5-Oberfläche."""

    result = await reference.search_page(payload, request)
    result["worker"] = {**(result.get("worker") or {}), **identity()}
    result["deployment_identity"] = identity()
    return result


async def search_module_page(
    payload: ModulePageRequest,
    request: Request,
) -> ModulePageResponse:
    """Öffentliche module-v1-Seitensuche."""

    trace_id = request.headers.get("cf-ray") or request.headers.get("x-request-id") or "local"
    trace = DebugTrace(payload.debug, trace_id)
    trace.mark("module_request_validated", page=payload.page, source=payload.source)
    legacy_dict = payload.profile.to_legacy_payload(page=payload.page, source=payload.source)
    legacy_payload = SearchRequest.model_validate(legacy_dict)
    trace.mark("legacy_payload_validated")
    result = await reference.search_page(legacy_payload, request)
    trace.mark("reference_search_completed")
    result["deployment_identity"] = identity()
    result["worker"] = {**(result.get("worker") or {}), **identity()}
    return module_response_from_legacy(result, payload, trace)


def validate_module_profile(profile: ModuleSearchProfile) -> dict[str, Any]:
    return {
        "contract": MODULE_CONTRACT,
        "valid": True,
        "profile": profile.model_dump(mode="json"),
        "legacy_payload": profile.to_legacy_payload(),
        "empty_fields_ignored": True,
    }


def run_module_self_tests() -> dict[str, Any]:
    result = run_contract_self_tests()
    adapter_checks: list[dict[str, Any]] = []

    evercade = evercade_profile("Interplay Collection 1", market_value=30)
    adapter_checks.append(
        {
            "name": "evercade_adapter",
            "ok": evercade.query.startswith("Evercade ") and evercade.market_value == 30,
        }
    )
    snes = snes_pal_profile("Super Metroid", market_value=70)
    adapter_checks.append(
        {
            "name": "snes_adapter",
            "ok": "PAL" in snes.required_terms and "NTSC" in snes.excluded_terms,
        }
    )
    result["checks"].extend(adapter_checks)
    result["ok"] = bool(result["ok"] and all(item["ok"] for item in adapter_checks))
    result["deployment"] = identity()
    return result


__all__ = [
    "SearchRequest",
    "search_page",
    "search_module_page",
    "validate_module_profile",
    "run_module_self_tests",
    "VERSION",
    "BUILD_ID",
    "API_CONTRACT",
]
