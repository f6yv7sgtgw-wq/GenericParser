"""Cloudflare bootstrap for GenericParser 0.45 module v1.

Die bestehende /api/search-Route bleibt kompatibel zur stabilen Referenz
0.44.6.5. Neue Projekte verwenden /api/module/v1/*. Debugdaten und
netzwerkfreie Selbsttests sind standardmäßig deaktiviert.
"""
from __future__ import annotations

import importlib
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .build_identity_v0450 import (
    API_CONTRACT,
    BOOTSTRAP_MODULE,
    BUILD_ID,
    ENTRYPOINT,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    TECHNICAL_BASE,
    VERSION,
    WORKER_UNIT,
)
from .module_api import MODULE_CONTRACT, ModulePageRequest, ModuleSearchProfile

app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)
_service: Any | None = None
_last_error: dict[str, str] | None = None


def identity() -> dict[str, Any]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "module_contract": MODULE_CONTRACT,
        "entrypoint": ENTRYPOINT,
        "bootstrap_module": BOOTSTRAP_MODULE,
        "search_module": SEARCH_MODULE,
        "worker_unit": WORKER_UNIT,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "technical_base": TECHNICAL_BASE,
        "module_release": True,
        "search_behavior_changed": False,
    }


def headers() -> dict[str, str]:
    return {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Module-Contract": MODULE_CONTRACT,
        "Cache-Control": "no-store",
    }


def respond(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=headers())


def failure(request: Request, detail: str, phase: str, exc: Exception | None = None) -> JSONResponse:
    return respond(
        500,
        {
            "detail": detail,
            "retryable": False,
            "error_type": type(exc).__name__ if exc else "WorkerError",
            "phase": phase,
            "ray_id": request.headers.get("cf-ray"),
            "worker": identity(),
        },
    )


def enabled_header(request: Request, name: str) -> bool:
    return request.headers.get(name, "").strip().casefold() in {"1", "true", "yes", "on"}


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


@app.get("/health")
@app.get("/api/version")
async def version() -> JSONResponse:
    return respond(
        200,
        {
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
            "legacy_search_endpoint": "/api/search",
            "module_endpoints": {
                "capabilities": "/api/module/v1/capabilities",
                "profile_validate": "/api/module/v1/profile/validate",
                "search": "/api/module/v1/search",
                "self_test": "/api/module/v1/self-test?enabled=true",
            },
            "debug_logging": {
                "enabled_by_default": False,
                "request_header": "X-GenericParser-Debug: 1",
                "module_request_field": "debug.enabled",
                "payload_logging_by_default": False,
            },
            "contract_tests": {
                "enabled_by_default": False,
                "network_used": False,
                "activation": "enabled=true or X-GenericParser-Tests: 1",
            },
            "controller_recovery": {
                "enabled": True,
                "mode": "stable-04465-single-saved-state-auto-resume",
                "quiet_period_ms": 90000,
                "max_auto_resumes": 1,
                "search_core_changed": False,
            },
            "last_import_error": _last_error,
        },
    )


@app.get("/api/module/v1/capabilities")
async def capabilities() -> JSONResponse:
    return respond(
        200,
        {
            "contract": MODULE_CONTRACT,
            "sources": ["kleinanzeigen"],
            "integrations": ["evercade", "snes-pal"],
            "pagination": "one-work-packet-per-request",
            "packet_size": 7,
            "debug_default": False,
            "tests_default": False,
            "legacy_reference": OPERATIONAL_REFERENCE,
            "functional_reference": FUNCTIONAL_REFERENCE,
            "deployment": identity(),
        },
    )


@app.post("/api/search")
async def legacy_search(request: Request) -> JSONResponse:
    """Unveränderter Suchvertrag der 0.44.6.5-Oberfläche."""

    started = perf_counter()
    debug_enabled = enabled_header(request, "x-genericparser-debug")
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
        if debug_enabled:
            result["debug"] = {
                "enabled": True,
                "trace_id": request.headers.get("cf-ray") or "local",
                "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                "phase": "legacy_reference_search",
                "payload_included": False,
            }
        return respond(200, result)
    except Exception as exc:
        return failure(request, "Arbeitspaket konnte nicht verarbeitet werden.", "reference_0444_flow", exc)


@app.post("/api/module/v1/profile/validate")
async def validate_profile(profile: ModuleSearchProfile, request: Request) -> JSONResponse:
    try:
        service = load_service()
        return respond(200, service.validate_module_profile(profile))
    except Exception as exc:
        return failure(request, "Modulprofil konnte nicht validiert werden.", "module_profile_validation", exc)


@app.post("/api/module/v1/search")
async def module_search(payload: ModulePageRequest, request: Request) -> JSONResponse:
    try:
        service = load_service()
        result = await service.search_module_page(payload, request)
        return respond(200, result.model_dump(mode="json", exclude_none=True))
    except Exception as exc:
        return failure(request, "Modulsuche konnte nicht verarbeitet werden.", "module_v1_search", exc)


@app.get("/api/module/v1/self-test")
async def module_self_test(request: Request, enabled: bool = False) -> JSONResponse:
    active = enabled or enabled_header(request, "x-genericparser-tests")
    if not active:
        return respond(
            409,
            {
                "contract": MODULE_CONTRACT,
                "ok": False,
                "tests_enabled": False,
                "detail": "Modultests sind standardmäßig deaktiviert.",
                "activation": "enabled=true or X-GenericParser-Tests: 1",
                "network_used": False,
            },
        )
    try:
        service = load_service()
        result = service.run_module_self_tests()
        result["tests_enabled"] = True
        return respond(200 if result.get("ok") else 500, result)
    except Exception as exc:
        return failure(request, "Modul-Selbsttest ist fehlgeschlagen.", "module_self_test", exc)
