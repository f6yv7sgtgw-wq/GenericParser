"""GenericParser 0.44.6.6 Build 2 wrapper around the unchanged 0.44.4 core.

Search, extraction, pagination, matching and traffic-light evaluation remain
identical to 0.44.6.5. The only test behavior lives in the browser controller:
a 90-second replacement for the regular page delay at 120, 240, 360 and every
further multiple of 120 unique results.
"""
from __future__ import annotations

from typing import Any
from fastapi import Request

from . import search_service_v0444 as reference
from .build_identity_v04466 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    VERSION,
    WORKER_UNIT,
)

SearchRequest = reference.SearchRequest


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await reference.search_page(payload, request)
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "diagnostic_mode": "reference_optional",
        "coverage_schema_required": False,
        "controller_auto_resume": True,
        "search_behavior_changed": False,
        "cooldown_test_server_change": False,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "diagnostic_mode": "reference_optional",
        "controller_auto_resume": True,
        "cooldown_test_server_change": False,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
