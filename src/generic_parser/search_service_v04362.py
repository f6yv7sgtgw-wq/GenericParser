"""GenericParser 0.43.6.2 search service.

The proven 0.43.6.1 extraction, pagination, diagnostics and result information
remain unchanged. This module only applies the 0.43.6.2 deployment identity.
"""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v04361 as previous
from .build_identity_v04362 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = previous.SearchRequest

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await previous.search_page(payload, request)
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "compact_ui": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
