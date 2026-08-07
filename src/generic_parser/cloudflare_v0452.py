"""GenericParser 0.45.2 Build 3 transport wrapper.

This module deliberately imports the live-proven 0.45.0 FastAPI application at
module startup. It does not lazy-import FastAPI/ASGI inside a request. The
0.45.0 search runtime and service stay untouched; this wrapper adds only CORS,
diagnostics, request tracing and compatibility aliases required by browser
clients.
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
    module_search as search_module_v1,
)
from .module_api import MODULE_CONTRACT, ModulePageRequest

app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)

EXPOSE_HEADERS = [
    "X-Request-ID",
    "X-GenericParser-Version",
    "X-GenericParser-Build",
    "X-GenericParser-Contract",
    "X-GenericParser-Module-Contract",
    "CF-Ray",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "X-GenericParser-Contract",
        "X-GenericParser-Token",
        "X-GenericParser-Debug",
        "X-GenericParser-Tests",
        "X-Request-ID",
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
            },
            "routes": {
                "health": "/health",
                "version": "/version",
                "diagnostics": "/diagnostics",
                "search": ["/search", "/api/search", "/api/module/search", "/api/module/v1/search"],
            },
        },
    )


@app.post("/search")
async def root_search(request: Request) -> JSONResponse:
    return await search_legacy(request)


@app.post("/api/module/search")
async def module_search_alias(payload: ModulePageRequest, request: Request) -> JSONResponse:
    return await search_module_v1(payload, request)


# Everything else, especially /api/search, /api/module/v1/* and the complete
# proven search implementation, is served by the unchanged 0.45.0 app.
app.mount("/", search_app)
