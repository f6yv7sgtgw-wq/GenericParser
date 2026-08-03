"""GenericParser 0.44.2 search service.

Technical behavior is inherited unchanged from the proven 0.43.6.3 service.
Only deployment identity is updated.
"""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v04363 as previous
from .build_identity_v0442 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

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
        "technical_base": "0.43.6.3",
        "runtime_card_patch": False,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
        "technical_base": "0.43.6.3",
    }
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
