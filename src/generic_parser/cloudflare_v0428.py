"""GenericParser 0.42.8 standalone Free-plan bootstrap."""
from __future__ import annotations

import importlib
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .build_identity_v0428 import API_CONTRACT, BUILD_ID, BUILD_REVISION, VERSION

SERVICE_MODULE = "generic_parser.search_service_v0428"
WORKER_UNIT = "standalone-bootstrap+free-cpu-work-packets+natural-end-guard"
app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)
_service: Any | None = None
_last_error: dict[str, Any] | None = None


def identity() -> dict[str, Any]:
    return {"version": VERSION, "build_id": BUILD_ID, "build_revision": BUILD_REVISION, "api_contract": API_CONTRACT}


def headers() -> dict[str, str]:
    return {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Commit": str(BUILD_REVISION),
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Bootstrap": "free-cpu-natural-end-guard",
    }


def respond(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=headers())


def failure(request: Request, *, status: int, detail: str, phase: str, exc: Exception | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "detail": detail,
        "retryable": False,
        "error_type": type(exc).__name__ if exc else "WorkerError",
        "phase": phase,
        "ray_id": request.headers.get("cf-ray"),
        "worker": {**identity(), "worker_unit": WORKER_UNIT},
    }
    if exc:
        body["traceback"] = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-6000:]
    return respond(status, body)


@app.get("/health")
@app.get("/api/version")
async def version() -> JSONResponse:
    return respond(200, {
        "status": "ok", **identity(), "worker_unit": WORKER_UNIT,
        "search_ready": True, "service_loaded": _service is not None,
        "service_module": SERVICE_MODULE, "free_plan_mode": True,
        "packet_size": 7, "reported_total_stop_disabled": True,
        "natural_end_guard": "empty_or_short_source_page",
        "last_import_error": _last_error,
    })


@app.get("/api/import-status")
async def import_status() -> JSONResponse:
    return respond(200, {"status": "ok", **identity(), "module": SERVICE_MODULE, "loaded": _service is not None, "last_error": _last_error})


def load_service() -> Any:
    global _service, _last_error
    if _service is not None:
        return _service
    try:
        service = importlib.import_module(SERVICE_MODULE)
        if getattr(service, "API_CONTRACT", None) != API_CONTRACT:
            raise RuntimeError("Search-service contract mismatch")
        _service = service
        _last_error = None
        return service
    except Exception as exc:
        _last_error = {"type": type(exc).__name__, "message": str(exc), "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]}
        raise


@app.post("/api/search")
async def search(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        service = load_service()
        payload = service.SearchRequest.model_validate(body)
        result = await service.search_page(payload, request)
    except Exception as exc:
        return failure(request, status=500, detail="Arbeitspaket konnte nicht verarbeitet werden.", phase="free_cpu_natural_end_packet", exc=exc)
    summary = result.get("summary") or {}
    pagination = result.get("pagination") or {}
    listings = result.get("listings") or []
    fetched = int(summary.get("fetched_listings") or 0)
    visible = int(summary.get("visible_listings") or 0)
    hidden = int(summary.get("hidden_by_filter") or 0)
    unique = int(pagination.get("unique_listings") or 0)
    consistent = bool(summary.get("data_consistent")) and fetched == visible + hidden and fetched == unique and visible == len(listings)
    if not consistent:
        return failure(request, status=500, detail="Arbeitspaket ist inkonsistent.", phase="response_consistency")
    result["worker"] = {**(result.get("worker") or {}), **identity(), "worker_unit": WORKER_UNIT, "free_plan_mode": True}
    return respond(200, result)


@app.exception_handler(Exception)
async def uncaught(request: Request, exc: Exception) -> JSONResponse:
    return failure(request, status=500, detail="Unbehandelte Bootstrap-Ausnahme.", phase="standalone_bootstrap", exc=exc)


__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
