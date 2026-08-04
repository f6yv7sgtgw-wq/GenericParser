"""GenericParser 0.44.6 functional rollback to the proven 0.44.4 core.

Search, extraction, real next-link pagination, diagnostics and active-rule
traffic-light evaluation are delegated unchanged to 0.44.4. This module only
applies the 0.44.6 deployment identity.
"""
from __future__ import annotations

from typing import Any
from fastapi import Request

from . import search_service_v0444 as reference
from .build_identity_v0446 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
    SEARCH_MODULE,
    TECHNICAL_BASE,
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
        "technical_base": TECHNICAL_BASE,
        "functional_rollback": True,
        "experimental_0445_runtime": False,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "technical_base": TECHNICAL_BASE,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
