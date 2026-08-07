"""Cloudflare bootstrap for GenericParser 0.45.1 infrastructure stabilization.

Search, matching, pagination and scoring remain on the 0.45.0/0.44.6.5
reference path. This release only adds browser-safe CORS, route aliases,
request tracing, diagnostics and consistent deployment identity.
"""
from __future__ import annotations

import importlib
import json
import traceback
import uuid
from datetime import UTC, datetime
from hmac import compare_digest
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .build_identity_v0451 import (
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
_started_at = datetime.now(UTC).isoformat()

CORS_ALLOW_ORIGIN = "*"
CORS_ALLOW_METHODS = "GET, POST, OPTIONS"
CORS_ALLOW_HEADERS = ", ".join(
    [
        "Accept",
        "Content-Type",
        "X-GenericParser-Contract",
        "X-GenericParser-Token",
        "X-GenericParser-Debug",
        "X-GenericParser-Tests",
        "X-Request-ID",
    ]
)
CORS_EXPOSE_HEADERS = ", ".join(
    [
        "X-Request-ID",
        "X-GenericParser-Version",
        "X-GenericParser-Build",
        "X-GenericParser-Contract",
        "X-GenericParser-Module-Contract",
        "CF-Ray",
    ]
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


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
        "infrastructure_release": True,
        "search_behavior_changed": False,
    }


def request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if value:
        return str(value)
    value = request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    request.state.request_id = value
    return value


def headers(request: Request | None = None) -> dict[str, str]:
    result = {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Module-Contract": MODULE_CONTRACT,
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
        "Access-Control-Allow-Methods": CORS_ALLOW_METHODS,
        "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
        "Access-Control-Expose-Headers": CORS_EXPOSE_HEADERS,
        "Access-Control-Max-Age": "86400",
    }
    if request is not None:
        result["X-Request-ID"] = request_id(request)
    return result


def respond(status: int, body: dict[str, Any], request: Request | None = None) -> JSONResponse:
    if request is not None:
        body.setdefault("request_id", request_id(request))
        body.setdefault("timestamp", utc_now())
    return JSONResponse(status_code=status, content=body, headers=headers(request))


def log_request(request: Request, *, status: int, elapsed_ms: float, error: str | None = None, stack: str | None = None) -> None:
    record = {
        "request_id": request_id(request),
        "timestamp": utc_now(),
        "route": request.url.path,
        "method": request.method,
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "duration_ms": round(elapsed_ms, 3),
        "http_status": status,
        "hit_count": getattr(request.state, "hit_count", None),
        "error": error or getattr(request.state, "error", None),
        "stacktrace": stack or getattr(request.state, "error_stack", None),
    }
    print(json.dumps({"genericparser_request": record}, ensure_ascii=False, default=str))


@app.middleware("http")
async def infrastructure_middleware(request: Request, call_next):
    request_id(request)
    started = perf_counter()
    if request.method == "OPTIONS":
        response: Response = Response(status_code=204, headers=headers(request))
        log_request(request, status=204, elapsed_ms=(perf_counter() - started) * 1000)
        return response
    try:
        response = await call_next(request)
        for name, value in headers(request).items():
            response.headers[name] = value
        log_request(request, status=response.status_code, elapsed_ms=(perf_counter() - started) * 1000)
        return response
    except Exception as exc:
        stack = traceback.format_exc()
        log_request(
            request,
            status=500,
            elapsed_ms=(perf_counter() - started) * 1000,
            error=f"{type(exc).__name__}: {exc}",
            stack=stack,
        )
        return respond(
            500,
            {
                "status": "error",
                "detail": "Interner Workerfehler.",
                "error_type": type(exc).__name__,
                "retryable": False,
            },
            request,
        )


def failure(request: Request, detail: str, phase: str, exc: Exception | None = None) -> JSONResponse:
    request.state.error = detail if exc is None else f"{type(exc).__name__}: {exc}"
    if exc is not None:
        request.state.error_stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return respond(
        500,
        {
            "status": "error",
            "detail": detail,
            "retryable": False,
            "error_type": type(exc).__name__ if exc else "WorkerError",
            "phase": phase,
            "ray_id": request.headers.get("cf-ray"),
            "worker": identity(),
        },
        request,
    )


def enabled_header(request: Request, name: str) -> bool:
    return request.headers.get(name, "").strip().casefold() in {"1", "true", "yes", "on"}


def _env_value(request: Request, name: str) -> str | None:
    env = request.scope.get("env")
    value = getattr(env, name, None) if env is not None else None
    if value is None and isinstance(env, dict):
        value = env.get(name)
    return str(value) if value not in (None, "") else None


def _authenticate_search(request: Request) -> JSONResponse | None:
    expected = _env_value(request, "APP_TOKEN")
    supplied = request.headers.get("x-genericparser-token", "")
    if expected is None or compare_digest(supplied, expected):
        return None
    return respond(
        401,
        {
            "status": "error",
            "contract": MODULE_CONTRACT,
            "detail": "Zugriffstoken fehlt oder ist ungültig.",
            "retryable": False,
            "error_type": "AuthenticationError",
            "phase": "authentication",
            "worker": identity(),
        },
        request,
    )


def load_service() -> Any:
    global _service, _last_error
    if _service is not None:
        return _service
    try:
        service = importlib.import_module(SEARCH_MODULE)
        expected = ("0.45.0", "gp-0450-20260805-1", API_CONTRACT)
        actual = (
            getattr(service, "VERSION", None),
            getattr(service, "BUILD_ID", None),
            getattr(service, "API_CONTRACT", None),
        )
        if actual != expected:
            raise RuntimeError(f"Search-service reference identity mismatch: {actual}")
        _service = service
        _last_error = None
        return service
    except Exception as exc:
        _last_error = {"type": type(exc).__name__, "message": str(exc)}
        raise


def health_payload() -> dict[str, Any]:
    return {
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
        "cors": {
            "allow_origin": CORS_ALLOW_ORIGIN,
            "allow_methods": CORS_ALLOW_METHODS,
            "allow_headers": CORS_ALLOW_HEADERS,
            "preflight": True,
        },
        "last_import_error": _last_error,
    }


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    return respond(200, health_payload(), request)


@app.get("/version")
@app.get("/api/version")
async def version(request: Request) -> JSONResponse:
    return respond(200, {"status": "ok", **identity()}, request)


@app.get("/diagnostics")
async def diagnostics(request: Request) -> JSONResponse:
    checks = {
        "health": True,
        "version": VERSION,
        "routing": True,
        "api": True,
        "module_contract": MODULE_CONTRACT,
        "cors": True,
        "preflight": True,
        "search_service_reference": "0.45.0",
        "search_behavior_changed": False,
    }
    return respond(
        200,
        {
            "status": "ok",
            "started_at": _started_at,
            "checks": checks,
            "routes": {
                "health": "/health",
                "version": "/version",
                "diagnostics": "/diagnostics",
                "search": ["/search", "/api/search", "/api/module/search", "/api/module/v1/search"],
            },
            "worker": identity(),
        },
        request,
    )


@app.get("/api/module/v1/capabilities")
async def capabilities(request: Request) -> JSONResponse:
    return respond(
        200,
        {
            "status": "ok",
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
        request,
    )


@app.post("/search")
@app.post("/api/search")
async def legacy_search(request: Request) -> JSONResponse:
    auth_failure = _authenticate_search(request)
    if auth_failure is not None:
        return auth_failure
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
        request.state.hit_count = len(listings)
        if fetched != visible + hidden or visible != len(listings) or fetched != unique:
            return failure(request, "Arbeitspaket ist inkonsistent.", "response_consistency")
        if debug_enabled:
            result["debug"] = {
                "enabled": True,
                "trace_id": request_id(request),
                "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                "phase": "legacy_reference_search",
                "payload_included": False,
            }
        return respond(200, result, request)
    except Exception as exc:
        return failure(request, "Arbeitspaket konnte nicht verarbeitet werden.", "reference_0444_flow", exc)


@app.post("/api/module/v1/profile/validate")
async def validate_profile(profile: ModuleSearchProfile, request: Request) -> JSONResponse:
    try:
        service = load_service()
        return respond(200, service.validate_module_profile(profile), request)
    except Exception as exc:
        return failure(request, "Modulprofil konnte nicht validiert werden.", "module_profile_validation", exc)


@app.post("/api/module/search")
@app.post("/api/module/v1/search")
async def module_search(payload: ModulePageRequest, request: Request) -> JSONResponse:
    auth_failure = _authenticate_search(request)
    if auth_failure is not None:
        return auth_failure
    try:
        service = load_service()
        result = await service.search_module_page(payload, request)
        body = result.model_dump(mode="json", exclude_none=True)
        request.state.hit_count = len(body.get("listings") or [])
        return respond(200, body, request)
    except Exception as exc:
        return failure(request, "Modulsuche konnte nicht verarbeitet werden.", "module_v1_search", exc)


@app.get("/api/module/v1/self-test")
async def module_self_test(request: Request, enabled: bool = False) -> JSONResponse:
    active = enabled or enabled_header(request, "x-genericparser-tests")
    if not active:
        return respond(
            409,
            {
                "status": "disabled",
                "contract": MODULE_CONTRACT,
                "ok": False,
                "tests_enabled": False,
                "detail": "Modultests sind standardmäßig deaktiviert.",
                "activation": "enabled=true or X-GenericParser-Tests: 1",
                "network_used": False,
            },
            request,
        )
    try:
        service = load_service()
        result = service.run_module_self_tests()
        result["tests_enabled"] = True
        return respond(200 if result.get("ok") else 500, result, request)
    except Exception as exc:
        return failure(request, "Modul-Selbsttest ist fehlgeschlagen.", "module_self_test", exc)
