"""GenericParser 0.44.6.4 Cloudflare bootstrap.

The proven 0.44.4 search path remains unchanged. The fix removes two recovery
failure sources seen in 0.44.6.3:

* the Worker entrypoint no longer executes the package ``__init__`` before ASGI;
* the recovery probe no longer imports the complete search-service chain.

The actual search service remains lazy and is imported only by ``/api/search``.
"""
from __future__ import annotations

import importlib
import json
import sys
import time
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .build_identity_v04464 import (
    API_CONTRACT,
    BOOTSTRAP_MODULE,
    BUILD_ID,
    ENTRYPOINT,
    FUNCTIONAL_REFERENCE,
    RECOVERY_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    TECHNICAL_BASE,
    VERSION,
    WORKER_UNIT,
)

app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)
_service: Any | None = None
_last_error: dict[str, Any] | None = None


def identity() -> dict[str, Any]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "entrypoint": ENTRYPOINT,
        "bootstrap_module": BOOTSTRAP_MODULE,
        "search_module": SEARCH_MODULE,
        "worker_unit": WORKER_UNIT,
        "reference_version": FUNCTIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "recovery_reference": RECOVERY_REFERENCE,
        "technical_base": TECHNICAL_BASE,
    }


def headers() -> dict[str, str]:
    return {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Bootstrap": "lazy-package-no-init",
        "Cache-Control": "no-store",
    }


def respond(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=headers())


def _safe_message(exc: Exception | None) -> str | None:
    if exc is None:
        return None
    return str(exc).replace("\n", " ")[:500]


def _record_error(phase: str, exc: Exception) -> dict[str, Any]:
    global _last_error
    diagnostic = {
        "phase": phase,
        "type": type(exc).__name__,
        "message": _safe_message(exc),
        "traceback": traceback.format_exc(limit=8)[-4000:],
        "timestamp_ms": int(time.time() * 1000),
    }
    _last_error = diagnostic
    try:
        print("GENERICPARSER_ERROR " + json.dumps(diagnostic, ensure_ascii=False))
    except Exception:
        pass
    return diagnostic


def failure(
    request: Request,
    detail: str,
    phase: str,
    exc: Exception | None = None,
    *,
    status: int = 500,
    retryable: bool = False,
) -> JSONResponse:
    diagnostic = _record_error(phase, exc) if exc is not None else None
    return respond(
        status,
        {
            "detail": detail,
            "retryable": retryable,
            "error_type": type(exc).__name__ if exc else "WorkerError",
            "error_message": _safe_message(exc),
            "phase": phase,
            "ray_id": request.headers.get("cf-ray"),
            "worker": identity(),
            "diagnostic": diagnostic,
        },
    )


@app.get("/health")
@app.get("/api/version")
async def version() -> JSONResponse:
    return respond(
        200,
        {
            "status": "ok",
            **identity(),
            "bootstrap_ready": True,
            "search_ready": True,
            "service_loaded": _service is not None,
            "lazy_search_import": True,
            "package_init_executed": False,
            "packet_size": 7,
            "pause_ms": 5000,
            "pagination_strategy": "source_html_weiter_link",
            "functional_reference": FUNCTIONAL_REFERENCE,
            "traffic_light_model": "v2-active-rules",
            "empty_fields_ignored": True,
            "functional_rollback": True,
            "experimental_0445_runtime": False,
            "diagnostic_mode": "reference_optional",
            "coverage_schema_required": False,
            "coverage_schema": None,
            "html_503_classification": "temporary_upstream_or_cloudflare_response",
            "controller_recovery": {
                "enabled": True,
                "mode": "staged-saved-state-auto-resume-light-probe",
                "triggers": ["cloudflare_1101", "cloudflare_1102", "retry_exhausted_after_repeated_html_503"],
                "probe_endpoint": "/api/recovery-probe",
                "probe_mode": "bootstrap_lazy",
                "probe_imports_search_service": False,
                "backoff_ms": [90000, 180000, 360000],
                "jitter_ratio": 0.10,
                "probe_intervals_ms": [30000, 60000, 120000],
                "max_probe_attempts": 3,
                "max_auto_resumes": 2,
                "classify_headers": ["cf-error-type", "cf-error-origin", "retry-after", "cf-ray"],
                "search_core_changed": False,
            },
            "last_import_error": _last_error,
        },
    )


@app.get("/api/recovery-probe")
async def recovery_probe(request: Request) -> JSONResponse:
    """Return bootstrap readiness without re-importing the heavy search chain."""
    started = time.perf_counter()
    checks = {
        "identity_consistent": bool(VERSION and BUILD_ID and API_CONTRACT),
        "asgi_app_ready": app is not None,
        "lazy_loader_ready": callable(load_service),
        "reference_core_declared": FUNCTIONAL_REFERENCE == "0.44.4",
        "package_init_skipped": "generic_parser" in sys.modules
        and not bool(getattr(sys.modules["generic_parser"], "__gp_init_executed__", False)),
    }
    ready = all(checks.values())
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    return respond(
        200 if ready else 503,
        {
            "status": "ready" if ready else "not_ready",
            **identity(),
            "bootstrap_ready": ready,
            "search_ready": ready,
            "lazy_search_import": True,
            "service_loaded": _service is not None,
            "reference_core_loaded": _service is not None,
            "reference_core_declared": True,
            "probe_mode": "bootstrap_lazy",
            "probe_imports_search_service": False,
            "checks": checks,
            "probe_duration_ms": duration_ms,
            "retryable": not ready,
            "ray_id": request.headers.get("cf-ray"),
            "last_import_error": _last_error,
        },
    )


def load_service() -> Any:
    global _service, _last_error
    if _service is not None:
        return _service
    try:
        importlib.invalidate_caches()
        service = importlib.import_module(SEARCH_MODULE)
        expected = (VERSION, BUILD_ID, API_CONTRACT)
        actual = (
            getattr(service, "VERSION", None),
            getattr(service, "BUILD_ID", None),
            getattr(service, "API_CONTRACT", None),
        )
        if actual != expected:
            raise RuntimeError(f"Search-service identity mismatch: {actual!r} != {expected!r}")
        if getattr(service, "REFERENCE_CORE_MODULE", None) != "generic_parser.search_service_v0444":
            raise RuntimeError("Search-service reference core mismatch")
        if getattr(service, "SEARCH_BEHAVIOR_CHANGED", None) is not False:
            raise RuntimeError("Search-service unexpectedly changes reference behavior")
        _service = service
        _last_error = None
        return service
    except Exception:
        sys.modules.pop(SEARCH_MODULE, None)
        raise


@app.post("/api/search")
async def search(request: Request) -> JSONResponse:
    try:
        service = load_service()
    except Exception as exc:
        return failure(
            request,
            "Search-Service konnte noch nicht geladen werden. Der Suchstand bleibt erhalten.",
            "search_service_import",
            exc,
            status=503,
            retryable=True,
        )

    try:
        payload = service.SearchRequest.model_validate(await request.json())
    except Exception as exc:
        return failure(request, "Suchauftrag ist ungültig.", "request_validation", exc, status=400)

    try:
        result = await service.search_page(payload, request)
    except Exception as exc:
        return failure(
            request,
            "Arbeitspaket konnte nicht verarbeitet werden.",
            "reference_0444_flow",
            exc,
            status=503,
            retryable=True,
        )

    summary = result.get("summary") or {}
    pagination = result.get("pagination") or {}
    listings = result.get("listings") or []
    fetched = int(summary.get("fetched_listings") or 0)
    visible = int(summary.get("visible_listings") or 0)
    hidden = int(summary.get("hidden_by_filter") or 0)
    unique = int(pagination.get("unique_listings") or 0)
    if fetched != visible + hidden or visible != len(listings) or fetched != unique:
        return failure(request, "Arbeitspaket ist inkonsistent.", "response_consistency")

    result["worker"] = {**(result.get("worker") or {}), **identity()}
    result["bootstrap"] = {
        "mode": "lazy-package-no-init",
        "package_init_executed": False,
        "service_loaded": True,
    }
    return respond(200, result)
