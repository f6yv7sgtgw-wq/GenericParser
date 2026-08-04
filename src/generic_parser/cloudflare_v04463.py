"""GenericParser 0.44.6.3 bootstrap with hardened controller recovery.

The proven 0.44.4 search path remains unchanged. This release adds a real
recovery probe that loads and validates the search service without contacting
Kleinanzeigen. Browser recovery uses staged backoff with jitter and at most
two automatic resume attempts.
"""
from __future__ import annotations

import importlib
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .build_identity_v04463 import (
    API_CONTRACT,
    BOOTSTRAP_MODULE,
    BUILD_ID,
    ENTRYPOINT,
    FUNCTIONAL_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    TECHNICAL_BASE,
    VERSION,
    WORKER_UNIT,
)

app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)
_service: Any | None = None
_last_error: dict[str, str] | None = None


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
        "technical_base": TECHNICAL_BASE,
    }


def headers() -> dict[str, str]:
    return {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": API_CONTRACT,
        "Cache-Control": "no-store",
    }


def respond(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=headers())


def failure(
    request: Request,
    detail: str,
    phase: str,
    exc: Exception | None = None,
    *,
    status: int = 500,
    retryable: bool = False,
) -> JSONResponse:
    return respond(status, {
        "detail": detail,
        "retryable": retryable,
        "error_type": type(exc).__name__ if exc else "WorkerError",
        "phase": phase,
        "ray_id": request.headers.get("cf-ray"),
        "worker": identity(),
    })


@app.get("/health")
@app.get("/api/version")
async def version() -> JSONResponse:
    return respond(200, {
        "status": "ok",
        **identity(),
        "search_ready": True,
        "service_loaded": _service is not None,
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
            "mode": "staged-saved-state-auto-resume",
            "triggers": ["cloudflare_1101", "cloudflare_1102", "retry_exhausted_after_repeated_html_503"],
            "probe_endpoint": "/api/recovery-probe",
            "backoff_ms": [90000, 180000, 360000],
            "jitter_ratio": 0.10,
            "probe_intervals_ms": [30000, 60000, 120000],
            "max_probe_attempts": 3,
            "max_auto_resumes": 2,
            "classify_headers": ["cf-error-type", "cf-error-origin", "retry-after", "cf-ray"],
            "search_core_changed": False,
        },
        "last_import_error": _last_error,
    })


def load_service() -> Any:
    global _service, _last_error
    if _service is not None:
        return _service
    try:
        service = importlib.import_module(SEARCH_MODULE)
        expected = (VERSION, BUILD_ID, API_CONTRACT)
        actual = (
            getattr(service, "VERSION", None),
            getattr(service, "BUILD_ID", None),
            getattr(service, "API_CONTRACT", None),
        )
        if actual != expected:
            raise RuntimeError("Search-service identity mismatch")
        _service = service
        _last_error = None
        return service
    except Exception as exc:
        _last_error = {"type": type(exc).__name__, "message": str(exc)}
        raise


@app.get("/api/recovery-probe")
async def recovery_probe(request: Request) -> JSONResponse:
    started = time.perf_counter()
    try:
        service = load_service()
        checks = {
            "service_module": getattr(service, "__name__", "") == SEARCH_MODULE,
            "request_model_ready": getattr(service, "SearchRequest", None) is not None,
            "search_callable": callable(getattr(service, "search_page", None)),
            "reference_core": getattr(service, "REFERENCE_CORE_MODULE", None) == "generic_parser.search_service_v0444",
            "search_behavior_unchanged": getattr(service, "SEARCH_BEHAVIOR_CHANGED", None) is False,
        }
        ready = all(checks.values())
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if not ready:
            return respond(503, {
                "status": "not_ready",
                **identity(),
                "retryable": True,
                "phase": "recovery_probe_validation",
                "checks": checks,
                "probe_duration_ms": duration_ms,
                "ray_id": request.headers.get("cf-ray"),
            })
        return respond(200, {
            "status": "ready",
            **identity(),
            "search_ready": True,
            "service_loaded": True,
            "reference_core_loaded": True,
            "checks": checks,
            "probe_duration_ms": duration_ms,
            "ray_id": request.headers.get("cf-ray"),
        })
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response = failure(
            request,
            "Search-Service ist für die Fortsetzung noch nicht bereit.",
            "recovery_probe_import",
            exc,
            status=503,
            retryable=True,
        )
        response.headers["X-GenericParser-Probe-Duration-Ms"] = str(duration_ms)
        return response


@app.post("/api/search")
async def search(request: Request) -> JSONResponse:
    try:
        service = load_service()
        payload = service.SearchRequest.model_validate(await request.json())
        result = await service.search_page(payload, request)
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
        return respond(200, result)
    except Exception as exc:
        return failure(request, "Arbeitspaket konnte nicht verarbeitet werden.", "reference_0444_flow", exc)
