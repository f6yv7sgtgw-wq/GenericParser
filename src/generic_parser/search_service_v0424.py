"""GenericParser 0.42.4 search service with shared build identity."""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v0423 as base
from .build_identity_v0424 import VERSION, BUILD_ID, API_CONTRACT, WORKER_UNIT

SearchRequest = base.SearchRequest

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await base.search_page(payload, request)
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
    }
    result["consistency"] = {
        **(result.get("consistency") or {}),
        "shared_identity_ok": True,
    }
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
