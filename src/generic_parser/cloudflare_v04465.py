"""GenericParser 0.44.6.5 clean rollback to the confirmed 0.44.6.2 runtime.

The proven 0.44.4 search path remains unchanged. Recovery behavior is the
single saved-state auto-resume from 0.44.6.2: after a terminal 503/1101 chain
the browser waits 90 seconds, probes /api/version and allows one automatic
resume. No 0.44.6.3 recovery probe or 0.44.6.4 lazy bootstrap is active.
"""
from __future__ import annotations

import importlib
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .build_identity_v04465 import (
    API_CONTRACT,
    BOOTSTRAP_MODULE,
    BUILD_ID,
    ENTRYPOINT,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
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
        "operational_reference": OPERATIONAL_REFERENCE,
        "technical_base": TECHNICAL_BASE,
        "clean_rollback": True,
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


def failure(request: Request, detail: str, phase: str, exc: Exception | None = None) -> JSONResponse:
    return respond(500, {
        "detail": detail,
        "retryable": False,
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
        "experimental_04463_recovery": False,
        "experimental_04464_lazy_bootstrap": False,
        "diagnostic_mode": "reference_optional",
        "coverage_schema_required": False,
        "coverage_schema": None,
        "html_503_classification": "temporary_upstream_or_cloudflare_response",
        "controller_recovery": {
            "enabled": True,
            "mode": "single_saved-state-auto-resume",
            "triggers": ["cloudflare_1101", "retry_exhausted_after_repeated_html_503"],
            "quiet_period_ms": 90000,
            "health_check_interval_ms": 15000,
            "max_health_checks": 4,
            "max_auto_resumes": 1,
            "probe_endpoint": "/api/version",
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
