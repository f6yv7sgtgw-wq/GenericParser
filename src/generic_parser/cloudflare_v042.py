"""GenericParser 0.42.0 – minimal bootstrap and lazy search-worker import.

The readiness endpoints do not import the parser, matching engine, HTTP client or
Kleinanzeigen source modules. Those modules are loaded only inside an active
/api/search or /api/location-id request, so import failures can be returned as
structured JSON instead of crashing the Cloudflare runtime before ASGI.
"""
from __future__ import annotations

import importlib
import time
import traceback
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

VERSION = "0.42.0"
BUILD_ID = "gp-0420-20260802-1"
BUILD_REVISION = BUILD_ID
API_CONTRACT = "match-v6.1-page-worker"
SEARCH_MODULE = "generic_parser.cloudflare_v039"

app = FastAPI(title="GenericParser Bootstrap Worker", version=VERSION, docs_url=None, redoc_url=None)
_search_module: Any | None = None
_import_error: dict[str, Any] | None = None


def _identity() -> dict[str, str]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "build_revision": BUILD_REVISION,
        "api_contract": API_CONTRACT,
    }


def _error_response(*, status: int, detail: str, error_type: str, phase: str, retryable: bool, request: Request, extra: dict[str, Any] | None = None) -> JSONResponse:
    content: dict[str, Any] = {
        "detail": detail,
        "retryable": retryable,
        "error_type": error_type,
        "phase": phase,
        "ray_id": request.headers.get("cf-ray"),
        "worker": {**_identity(), "worker_unit": "lazy-bootstrap"},
    }
    if extra:
        content.update(extra)
    return JSONResponse(status_code=status, content=content)


def _load_search_module() -> tuple[Any, int]:
    global _search_module, _import_error
    if _search_module is not None:
        return _search_module, 0
    started = time.perf_counter()
    try:
        module = importlib.import_module(SEARCH_MODULE)
        module.VERSION = VERSION
        _search_module = module
        _import_error = None
        return module, max(0, round((time.perf_counter() - started) * 1000))
    except Exception as exc:
        elapsed = max(0, round((time.perf_counter() - started) * 1000))
        _import_error = {
            "type": type(exc).__name__,
            "message": str(exc) or type(exc).__name__,
            "elapsed_ms": elapsed,
            "traceback": traceback.format_exception_only(type(exc), exc)[-1].strip(),
        }
        raise


@app.middleware("http")
async def identity_headers(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
    try:
        response = await call_next(request)
    except Exception as exc:
        response = _error_response(
            status=500,
            detail="Interner Bootstrap-Fehler wurde kontrolliert abgefangen.",
            error_type=type(exc).__name__,
            phase="bootstrap_asgi",
            retryable=False,
            request=request,
            extra={"traceback": traceback.format_exception_only(type(exc), exc)[-1].strip()},
        )
    response.headers["X-GenericParser-Version"] = VERSION
    response.headers["X-GenericParser-Build"] = BUILD_ID
    response.headers["X-GenericParser-Commit"] = BUILD_REVISION
    response.headers["X-GenericParser-Contract"] = API_CONTRACT
    response.headers["X-GenericParser-Bootstrap"] = "lazy-import"
    return response


@app.get("/health")
@app.get("/api/version")
async def version() -> dict[str, Any]:
    return {
        "status": "ok",
        **_identity(),
        "worker_unit": "lazy-bootstrap",
        "search_ready": True,
        "search_module_loaded": _search_module is not None,
        "last_import_error": _import_error,
    }


@app.get("/api/import-status")
async def import_status() -> dict[str, Any]:
    return {
        "status": "ok",
        **_identity(),
        "module": SEARCH_MODULE,
        "loaded": _search_module is not None,
        "last_error": _import_error,
    }


@app.post("/api/search")
async def search(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        return _error_response(status=400, detail="Ungültiger JSON-Request.", error_type=type(exc).__name__, phase="request_json", retryable=False, request=request)

    try:
        module, import_ms = _load_search_module()
    except Exception as exc:
        return _error_response(
            status=500,
            detail="Suchmodule konnten nicht geladen werden.",
            error_type=type(exc).__name__,
            phase="lazy_import_search_module",
            retryable=False,
            request=request,
            extra={"import": _import_error},
        )

    try:
        payload = module.SearchRequest.model_validate(body)
    except Exception as exc:
        return _error_response(status=422, detail="Suchrequest ist ungültig.", error_type=type(exc).__name__, phase="search_request_validation", retryable=False, request=request, extra={"validation": str(exc)[:1200], "import_ms": import_ms})

    try:
        result = await module.search(payload, request)
    except Exception as exc:
        return _error_response(
            status=500,
            detail="Seitenworker-Fehler wurde kontrolliert abgefangen.",
            error_type=type(exc).__name__,
            phase="page_worker_search",
            retryable=False,
            request=request,
            extra={"traceback": traceback.format_exception_only(type(exc), exc)[-1].strip(), "import_ms": import_ms},
        )

    if isinstance(result, dict):
        worker = dict(result.get("worker") or {})
        worker.update({**_identity(), "worker_unit": "lazy-bootstrap+one-page", "lazy_import_ms": import_ms})
        result["worker"] = worker
    return result


@app.post("/api/location-id")
async def location_id(request: Request):
    try:
        body = await request.json()
        module, import_ms = _load_search_module()
        payload = module.legacy.LocationRequest.model_validate(body)
        result = await module.location_id(payload, request)
        if isinstance(result, dict):
            result["worker"] = {**_identity(), "lazy_import_ms": import_ms}
        return result
    except Exception as exc:
        return _error_response(status=500, detail="Location-ID-Verarbeitung fehlgeschlagen.", error_type=type(exc).__name__, phase="location_id", retryable=False, request=request, extra={"traceback": traceback.format_exception_only(type(exc), exc)[-1].strip()})


__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
