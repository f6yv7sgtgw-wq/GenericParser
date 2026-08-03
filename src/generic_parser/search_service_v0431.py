"""GenericParser 0.43.1 search wrapper with central identity diagnostics."""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v0430 as base
from .build_identity_v0431 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, identity

SearchRequest = base.SearchRequest

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await base.search_page(payload, request)
    result["worker"] = {
        **(result.get("worker") or {}),
        **identity("search"),
        "module_name": SEARCH_MODULE,
        "legacy_service_version": getattr(base, "VERSION", None),
        "legacy_service_build": getattr(base, "BUILD_ID", None),
        "identity_source": "build_identity_v0431",
    }
    result["deployment_identity"] = {
        "search": identity("search"),
        "request_path": str(request.url.path),
        "cf_ray": request.headers.get("cf-ray"),
    }
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
