"""GenericParser 0.45.2 transport and compatibility wrapper.

Build 6 preserves the live-proven 0.45.0 FastAPI/search runtime and Build 5
Worker-edge CORS behavior. It adds only an Evercade compatibility adapter on
the unversioned /api/module/search alias. The canonical /api/module/v1/search
contract stays strict and unchanged.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .build_identity_v0452 import (
    API_CONTRACT,
    BOOTSTRAP_MODULE,
    BUILD_ID,
    ENTRYPOINT,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    SEARCH_RUNTIME,
    TECHNICAL_BASE,
    VERSION,
    WORKER_UNIT,
)
from .cloudflare_v0450 import (
    app as search_app,
    legacy_search as search_legacy,
    load_service,
    module_search as search_module_v1,
)
from .module_api import MODULE_CONTRACT, ModulePageRequest, ModuleSearchProfile
from .vinted_enrichment import DETAIL_BATCH_LIMIT, enrich_vinted_batch

app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)

EXPOSE_HEADERS = [
    "X-Request-ID",
    "X-GenericParser-Version",
    "X-GenericParser-Build",
    "X-GenericParser-Contract",
    "X-GenericParser-Module-Contract",
    "X-GenericParser-CORS-Layer",
    "CF-Ray",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "X-Generic-Parser-Contract",
        "X-Request-ID",
        "X-GenericParser-Contract",
        "X-GenericParser-Token",
        "X-GenericParser-Debug",
        "X-GenericParser-Tests",
    ],
    expose_headers=EXPOSE_HEADERS,
    max_age=86400,
)


def identity() -> dict[str, Any]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "module_contract": MODULE_CONTRACT,
        "entrypoint": ENTRYPOINT,
        "bootstrap_module": BOOTSTRAP_MODULE,
        "search_module": SEARCH_MODULE,
        "search_runtime": SEARCH_RUNTIME,
        "worker_unit": WORKER_UNIT,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "technical_base": TECHNICAL_BASE,
        "search_behavior_changed": False,
        "startup_model": "eager-asgi-0450",
        "evercade_alias_compatibility": True,
        "vinted_background_enrichment": True,
        "vinted_detail_batch_limit": DETAIL_BATCH_LIMIT,
    }


def release_headers(request_id: str) -> dict[str, str]:
    return {
        "X-Request-ID": request_id,
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Module-Contract": MODULE_CONTRACT,
        "Cache-Control": "no-store",
    }


def response(request_id: str, body: dict[str, Any], status: int = 200) -> JSONResponse:
    payload = dict(body)
    payload.setdefault("request_id", request_id)
    payload.setdefault("timestamp", datetime.now(UTC).isoformat())
    return JSONResponse(status_code=status, content=payload, headers=release_headers(request_id))


@app.middleware("http")
async def request_trace(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    try:
        result = await call_next(request)
        status = int(result.status_code)
        error = None
    except Exception as exc:
        status = 500
        error = f"{type(exc).__name__}: {exc}"
        result = response(
            request_id,
            {
                "status": "error",
                "detail": "GenericParser request failed.",
                "error_type": type(exc).__name__,
                "worker": identity(),
            },
            status=500,
        )
    for key, value in release_headers(request_id).items():
        result.headers[key] = value
    record = {
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "route": request.url.path,
        "method": request.method,
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "http_status": status,
        "error": error,
    }
    print(json.dumps({"genericparser_request": record}, ensure_ascii=False))
    return result


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    return response(
        request_id,
        {
            "status": "ok",
            **identity(),
            "cors": True,
            "preflight": True,
            "search_ready": True,
            "vinted_background_enrichment": True,
            "vinted_detail_batch_limit": DETAIL_BATCH_LIMIT,
        },
    )


@app.get("/version")
@app.get("/api/version")
async def version(request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    return response(request_id, {"status": "ok", **identity()})


@app.get("/diagnostics")
async def diagnostics(request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    return response(
        request_id,
        {
            "status": "ok",
            "worker": identity(),
            "checks": {
                "routing": True,
                "cors": True,
                "preflight": True,
                "module_contract": MODULE_CONTRACT,
                "search_runtime": SEARCH_RUNTIME,
                "startup_model": "eager-asgi-0450",
                "search_behavior_changed": False,
                "evercade_alias_compatibility": True,
                "vinted_background_enrichment": True,
                "vinted_detail_batch_limit": DETAIL_BATCH_LIMIT,
            },
            "routes": {
                "health": "/health",
                "version": "/version",
                "diagnostics": "/diagnostics",
                "search": ["/search", "/api/search", "/api/module/search", "/api/module/v1/search"],
                "vinted_detail_enrichment": "/api/vinted/enrich",
            },
        },
    )


@app.get("/api/module/v1/capabilities")
async def module_capabilities(request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    return response(
        request_id,
        {
            "contract": MODULE_CONTRACT,
            "sources": ["kleinanzeigen", "vinted"],
            "default_sources": ["kleinanzeigen", "vinted"],
            "integrations": ["evercade", "snes-pal"],
            "pagination": "one-work-packet-per-request",
            "vinted_detail_enrichment": {
                "inline_limit_per_catalog_page": DETAIL_BATCH_LIMIT,
                "background_endpoint": "/api/module/v1/vinted/enrich",
                "background_batch_limit": DETAIL_BATCH_LIMIT,
                "serial_batches": True,
                "blocks_search": False,
                "rescoring": True,
            },
            "deployment": identity(),
        },
    )


@app.post("/search")
async def root_search(request: Request) -> JSONResponse:
    return await search_legacy(request)


def _legacy_evercade_to_module(raw: dict[str, Any]) -> ModulePageRequest:
    """Translate the historical flat Evercade packet into module-contract v1.

    This compatibility is intentionally limited to the unversioned alias
    /api/module/search. The canonical /api/module/v1/search endpoint still
    requires an explicit `profile` object and therefore remains a strict,
    project-independent contract.
    """
    cartridge = raw.get("cartridge") if isinstance(raw.get("cartridge"), dict) else {}
    query = str(raw.get("query") or cartridge.get("title") or "").strip()
    if not query:
        raise ValueError("Evercade compatibility payload requires query or cartridge.title")

    profile_data: dict[str, Any] = {
        "profile_id": str(cartridge.get("key") or raw.get("profile_id") or "evercade-legacy"),
        "display_name": str(cartridge.get("title") or raw.get("display_name") or query),
        "query": query,
        "required_terms": raw.get("required_terms") or [],
        "excluded_terms": raw.get("excluded_terms") or [],
        "model_patterns": raw.get("model_patterns") or [],
        "brands": raw.get("brands") or [],
        "max_price": raw.get("max_price"),
        "market_value": raw.get("market_value"),
        "postal_code": raw.get("postal_code"),
        "location_id": raw.get("location_id"),
        "radius_km": raw.get("radius_km"),
        "accept_bundles": bool(raw.get("accept_bundles", False)),
        "accept_incomplete": bool(raw.get("accept_incomplete", False)),
        "include_review": bool(raw.get("include_review", True)),
        "include_rejected": bool(raw.get("include_rejected", True)),
        "sort_by": raw.get("sort_by") or "relevance",
    }
    # Omit null optionals so the canonical profile defaults/validators remain
    # the single source of truth.
    profile_data = {key: value for key, value in profile_data.items() if value is not None}
    profile = ModuleSearchProfile.model_validate(profile_data)
    return ModulePageRequest(
        profile=profile,
        page=int(raw.get("page") or 0),
        source=str(raw.get("source") or "auto"),
        debug=raw.get("debug") or {},
    )


@app.post("/api/module/search")
async def module_search_alias(request: Request) -> JSONResponse:
    """Compatibility alias accepting canonical and historical Evercade packets."""
    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    try:
        raw = await request.json()
        if not isinstance(raw, dict):
            raise ValueError("JSON request body must be an object")
        if "profile" in raw:
            payload = ModulePageRequest.model_validate(raw)
            compatibility_mode = "canonical"
        else:
            payload = _legacy_evercade_to_module(raw)
            compatibility_mode = "evercade-flat-v1"
        result = await search_module_v1(payload, request)
        result.headers["X-GenericParser-Compatibility"] = compatibility_mode
        result.headers["X-Request-ID"] = request_id
        return result
    except Exception as exc:
        return response(
            request_id,
            {
                "status": "error",
                "detail": "Modul-Alias konnte das Requestformat nicht verarbeiten.",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "accepted_formats": ["ModulePageRequest(profile=...)", "Evercade flat compatibility packet"],
                "worker": identity(),
            },
            status=422,
        )


@app.post("/api/module/v1/vinted/enrich")
@app.post("/api/vinted/enrich")
async def vinted_detail_enrichment(request: Request) -> JSONResponse:
    """Enrich one non-blocking Vinted detail batch and re-run scoring.

    This endpoint is intentionally separate from every search alias. A client
    first renders the catalog response and then calls this route serially with
    at most three already returned Vinted listings.
    """

    request_id = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    try:
        raw = await request.json()
        if not isinstance(raw, dict):
            raise ValueError("JSON request body must be an object")
        listings = raw.get("listings")
        search = raw.get("search")
        profile = raw.get("profile")
        if not isinstance(listings, list):
            raise ValueError("listings must be an array")
        service = load_service()
        if isinstance(search, dict):
            payload = service.SearchRequest.model_validate(search)
            request_format = "legacy-search-profile"
        elif isinstance(profile, dict):
            module_profile = ModuleSearchProfile.model_validate(profile)
            payload = service.SearchRequest.model_validate(
                module_profile.to_legacy_payload(page=int(raw.get("page") or 0), source="vinted")
            )
            request_format = "module-profile-v1"
        else:
            raise ValueError("search or profile must contain the original search profile")
        result = await enrich_vinted_batch(listings, payload)
        result["request_format"] = request_format
        result["contract"] = MODULE_CONTRACT
        result["worker"] = identity()
        return response(request_id, result)
    except ValueError as exc:
        return response(
            request_id,
            {
                "status": "error",
                "detail": str(exc),
                "error_type": type(exc).__name__,
                "retryable": False,
                "detail_batch_limit": DETAIL_BATCH_LIMIT,
                "worker": identity(),
            },
            status=422,
        )
    except Exception as exc:
        return response(
            request_id,
            {
                "status": "error",
                "detail": "Vinted-Hintergrundanreicherung konnte nicht verarbeitet werden.",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "retryable": False,
                "detail_batch_limit": DETAIL_BATCH_LIMIT,
                "worker": identity(),
            },
            status=502,
        )


# Everything else, especially /api/search, /api/module/v1/* and the complete
# proven search implementation, is served by the unchanged 0.45.0 app.
app.mount("/", search_app)
