"""GenericParser 0.42.6 standalone diagnostic bootstrap.

The readiness/version route has no dependency on parser or search modules.
The proven 0.42.3 search service is imported only for /api/search.
"""
from __future__ import annotations

import importlib
import time
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .build_identity_v0426 import API_CONTRACT, BUILD_ID, BUILD_REVISION, VERSION

SERVICE_MODULE = "generic_parser.search_service_v0423"
WORKER_UNIT = "standalone-bootstrap+lazy-search-service"

app = FastAPI(
    title=f"GenericParser {VERSION}",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
)

_service: Any | None = None
_last_import_error: dict[str, Any] | None = None


def identity() -> dict[str, Any]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "build_revision": BUILD_REVISION,
        "api_contract": API_CONTRACT,
    }


def response_headers() -> dict[str, str]:
    return {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Commit": str(BUILD_REVISION),
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Bootstrap": "standalone",
    }


def json_response(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=response_headers())


def error_response(
    request: Request,
    *,
    status: int,
    detail: str,
    error_type: str,
    phase: str,
    retryable: bool = False,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "detail": detail,
        "retryable": retryable,
        "error_type": error_type,
        "phase": phase,
        "ray_id": request.headers.get("cf-ray"),
        "worker": {**identity(), "worker_unit": WORKER_UNIT},
    }
    if extra:
        body.update(extra)
    return json_response(status, body)


@app.get("/health")
@app.get("/api/version")
async def version() -> JSONResponse:
    # Deliberately contains no dynamic import and no parser access.
    return json_response(
        200,
        {
            "status": "ok",
            **identity(),
            "worker_unit": WORKER_UNIT,
            "search_ready": True,
            "service_loaded": _service is not None,
            "service_module": SERVICE_MODULE,
            "last_import_error": _last_import_error,
        },
    )


@app.get("/api/import-status")
async def import_status() -> JSONResponse:
    return json_response(
        200,
        {
            "status": "ok",
            **identity(),
            "worker_unit": WORKER_UNIT,
            "module": SERVICE_MODULE,
            "loaded": _service is not None,
            "last_error": _last_import_error,
        },
    )


def load_service() -> tuple[Any, int]:
    global _service, _last_import_error
    if _service is not None:
        return _service, 0

    started = time.perf_counter()
    try:
        service = importlib.import_module(SERVICE_MODULE)
        if getattr(service, "API_CONTRACT", None) != API_CONTRACT:
            raise RuntimeError(
                f"Search-service contract mismatch: "
                f"{getattr(service, 'API_CONTRACT', None)!r}"
            )
        if not hasattr(service, "SearchRequest") or not hasattr(service, "search_page"):
            raise RuntimeError("Search-service interface is incomplete")
        _service = service
        _last_import_error = None
        return service, max(0, round((time.perf_counter() - started) * 1000))
    except Exception as exc:
        _last_import_error = {
            "type": type(exc).__name__,
            "message": str(exc) or type(exc).__name__,
            "elapsed_ms": max(0, round((time.perf_counter() - started) * 1000)),
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-6000:],
        }
        raise


@app.post("/api/search")
async def search(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception as exc:
        return error_response(
            request,
            status=400,
            detail="Ungültiger JSON-Request.",
            error_type=type(exc).__name__,
            phase="request_json",
        )

    try:
        service, import_ms = load_service()
    except Exception as exc:
        return error_response(
            request,
            status=500,
            detail="Search-Service konnte nicht geladen werden.",
            error_type=type(exc).__name__,
            phase="lazy_import_search_service",
            extra={"import": _last_import_error},
        )

    try:
        payload = service.SearchRequest.model_validate(body)
    except Exception as exc:
        return error_response(
            request,
            status=422,
            detail="Suchrequest ist ungültig.",
            error_type=type(exc).__name__,
            phase="search_request_validation",
            extra={"validation": str(exc)[:2000], "import_ms": import_ms},
        )

    try:
        result = await service.search_page(payload, request)
    except Exception as exc:
        return error_response(
            request,
            status=500,
            detail="Search-Service-Fehler wurde kontrolliert abgefangen.",
            error_type=type(exc).__name__,
            phase="search_service_page",
            extra={
                "traceback": "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )[-8000:],
                "import_ms": import_ms,
            },
        )

    summary = result.get("summary") or {}
    pagination = result.get("pagination") or {}
    listings = result.get("listings") or []
    fetched = int(summary.get("fetched_listings") or 0)
    visible = int(summary.get("visible_listings") or 0)
    hidden = int(summary.get("hidden_by_filter") or 0)
    unique = int(pagination.get("unique_listings") or 0)
    consistent = (
        bool(summary.get("data_consistent"))
        and fetched == visible + hidden
        and fetched == unique
        and visible == len(listings)
    )
    if not consistent:
        return error_response(
            request,
            status=500,
            detail="Seitendaten sind inkonsistent.",
            error_type="DataConsistencyError",
            phase="response_consistency",
            extra={
                "counts": {
                    "fetched": fetched,
                    "visible": visible,
                    "hidden": hidden,
                    "unique": unique,
                    "listings": len(listings),
                }
            },
        )

    result["worker"] = {
        **(result.get("worker") or {}),
        **identity(),
        "worker_unit": WORKER_UNIT,
        "search_service_version": getattr(service, "VERSION", None),
        "search_service_build": getattr(service, "BUILD_ID", None),
        "lazy_import_ms": import_ms,
    }
    result["consistency"] = {
        "ok": True,
        "fetched_equals_visible_plus_hidden": True,
        "fetched_equals_unique": True,
        "visible_equals_listings": True,
    }
    return json_response(200, result)


@app.exception_handler(Exception)
async def uncaught_exception(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        request,
        status=500,
        detail="Unbehandelte Bootstrap-Ausnahme wurde protokollierbar gemacht.",
        error_type=type(exc).__name__,
        phase="standalone_bootstrap",
        extra={
            "traceback": "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )[-8000:]
        },
    )


__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
