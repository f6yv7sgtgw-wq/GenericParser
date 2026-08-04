"""GenericParser 0.44.6.5 clean rollback wrapper.

Search, extraction, pagination, matching and traffic-light evaluation are
executed unchanged by ``search_service_v0444``. The runtime behavior is the
confirmed 0.44.6.2 path; this module changes deployment identity only.
"""
from __future__ import annotations

from typing import Any
from fastapi import Request

from . import search_service_v0444 as reference
from .build_identity_v04465 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
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
        "diagnostic_mode": "reference_optional",
        "coverage_schema_required": False,
        "controller_auto_resume": True,
        "search_behavior_changed": False,
        "clean_rollback": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "diagnostic_mode": "reference_optional",
        "controller_auto_resume": True,
        "clean_rollback": True,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
