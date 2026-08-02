"""GenericParser 0.42.2 – minimal bootstrap with app-free search service."""
from __future__ import annotations

import importlib
import time
import traceback
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

VERSION = "0.42.2"
BUILD_ID = "gp-0422-20260802-1"
BUILD_REVISION = BUILD_ID
API_CONTRACT = "match-v6.1-page-worker"
SERVICE_MODULE = "generic_parser.search_service_v0422"

app = FastAPI(title="GenericParser 0.42.2", version=VERSION, docs_url=None, redoc_url=None)
_service: Any | None = None
_import_error: dict[str, Any] | None = None


def identity() -> dict[str, str]:
    return {"version": VERSION, "build_id": BUILD_ID, "build_revision": BUILD_REVISION, "api_contract": API_CONTRACT}


def error_response(request: Request, *, status: int, detail: str, error_type: str, phase: str, retryable: bool, extra: dict[str, Any] | None = None) -> JSONResponse:
    body: dict[str, Any] = {"detail": detail, "retryable": retryable, "error_type": error_type, "phase": phase, "ray_id": request.headers.get("cf-ray"), "worker": {**identity(), "worker_unit": "bootstrap+app-free-service"}}
    if extra: body.update(extra)
    return JSONResponse(status_code=status, content=body)


def load_service() -> tuple[Any, int]:
    global _service, _import_error
    if _service is not None: return _service, 0
    started = time.perf_counter()
    try:
        service = importlib.import_module(SERVICE_MODULE)
        if service.VERSION != VERSION or service.BUILD_ID != BUILD_ID or service.API_CONTRACT != API_CONTRACT:
            raise RuntimeError(f"Service identity mismatch: {service.VERSION}/{service.BUILD_ID}/{service.API_CONTRACT}")
        _service = service
        _import_error = None
        return service, max(0, round((time.perf_counter()-started)*1000))
    except Exception as exc:
        _import_error = {"type": type(exc).__name__, "message": str(exc) or type(exc).__name__, "elapsed_ms": max(0, round((time.perf_counter()-started)*1000)), "traceback": traceback.format_exception_only(type(exc), exc)[-1].strip()}
        raise


@app.middleware("http")
async def identity_headers(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
    try:
        response = await call_next(request)
    except Exception as exc:
        response = error_response(request, status=500, detail="Bootstrap-Fehler wurde kontrolliert abgefangen.", error_type=type(exc).__name__, phase="bootstrap_asgi", retryable=False, extra={"traceback": traceback.format_exception_only(type(exc), exc)[-1].strip()})
    response.headers["X-GenericParser-Version"] = VERSION
    response.headers["X-GenericParser-Build"] = BUILD_ID
    response.headers["X-GenericParser-Commit"] = BUILD_REVISION
    response.headers["X-GenericParser-Contract"] = API_CONTRACT
    response.headers["X-GenericParser-Bootstrap"] = "app-free-service"
    return response


@app.get("/health")
@app.get("/api/version")
async def version() -> dict[str, Any]:
    return {"status": "ok", **identity(), "worker_unit": "bootstrap+app-free-service", "search_ready": True, "service_loaded": _service is not None, "last_import_error": _import_error}


@app.get("/api/import-status")
async def import_status() -> dict[str, Any]:
    return {"status": "ok", **identity(), "module": SERVICE_MODULE, "loaded": _service is not None, "last_error": _import_error}


@app.post("/api/search")
async def search(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        return error_response(request, status=400, detail="Ungültiger JSON-Request.", error_type=type(exc).__name__, phase="request_json", retryable=False)
    try:
        service, import_ms = load_service()
    except Exception as exc:
        return error_response(request, status=500, detail="App-freier Search-Service konnte nicht geladen werden.", error_type=type(exc).__name__, phase="lazy_import_search_service", retryable=False, extra={"import": _import_error})
    try:
        payload = service.SearchRequest.model_validate(body)
    except Exception as exc:
        return error_response(request, status=422, detail="Suchrequest ist ungültig.", error_type=type(exc).__name__, phase="search_request_validation", retryable=False, extra={"validation": str(exc)[:1200], "import_ms": import_ms})
    try:
        result = await service.search_page(payload, request)
    except Exception as exc:
        return error_response(request, status=500, detail="Search-Service-Fehler wurde kontrolliert abgefangen.", error_type=type(exc).__name__, phase="search_service_page", retryable=False, extra={"traceback": traceback.format_exception_only(type(exc), exc)[-1].strip(), "import_ms": import_ms})
    summary = result.get("summary") or {}
    pagination = result.get("pagination") or {}
    listings = result.get("listings") or []
    fetched = int(summary.get("fetched_listings") or 0)
    visible = int(summary.get("visible_listings") or 0)
    hidden = int(summary.get("hidden_by_filter") or 0)
    unique = int(pagination.get("unique_listings") or 0)
    consistent = bool(summary.get("data_consistent")) and fetched == visible + hidden and fetched == unique and visible == len(listings)
    if not consistent:
        return error_response(request, status=500, detail="Seitendaten sind inkonsistent.", error_type="DataConsistencyError", phase="response_consistency", retryable=False, extra={"counts": {"fetched": fetched, "visible": visible, "hidden": hidden, "unique": unique, "listings": len(listings)}})
    result["worker"] = {**(result.get("worker") or {}), **identity(), "worker_unit": "bootstrap+app-free-one-page-service", "lazy_import_ms": import_ms}
    result["consistency"] = {"ok": True, "fetched_equals_visible_plus_hidden": True, "fetched_equals_unique": True, "visible_equals_listings": True}
    return result


__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
