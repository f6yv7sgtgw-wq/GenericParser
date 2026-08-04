"""GenericParser 0.44.6.1 diagnostic-only wrapper around the 0.44.4 core.

Search, extraction, pagination, matching and traffic-light evaluation are
executed unchanged by ``search_service_v0444``. This module only updates the
deployment identity and declares the reference diagnostic mode.
"""
from __future__ import annotations

from typing import Any
from fastapi import Request

from . import search_service_v0444 as reference
from .build_identity_v04461 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
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
        "diagnostic_mode": "reference_optional",
        "coverage_schema_required": False,
        "search_behavior_changed": False,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "diagnostic_mode": "reference_optional",
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
