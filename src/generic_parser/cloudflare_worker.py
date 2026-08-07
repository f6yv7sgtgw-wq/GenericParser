"""Cloudflare-Python-Worker entrypoint for GenericParser 0.45.2.

0.45.2 adds a minimal raw Workers edge shell in front of the existing 0.45.1
ASGI application. Health/version/diagnostics and every OPTIONS request are
answered without importing FastAPI. Search traffic is delegated lazily to the
unchanged 0.45.1 infrastructure app and 0.45.0/0.44.6.5 search path.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import asgi
from workers import Response, WorkerEntrypoint

VERSION = "0.45.2"
BUILD_ID = "gp-0452-20260807-1"
CONTRACT = "generic-parser-module-v1"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Accept, Content-Type, X-GenericParser-Contract, X-GenericParser-Token, X-GenericParser-Debug, X-GenericParser-Tests, X-Request-ID",
    "Access-Control-Expose-Headers": "X-Request-ID, X-GenericParser-Version, X-GenericParser-Build, X-GenericParser-Contract, X-GenericParser-Module-Contract, CF-Ray",
    "Access-Control-Max-Age": "86400",
    "Cache-Control": "no-store",
}


def _load_generic_parser_package():
    package_name = "generic_parser"
    if package_name in sys.modules:
        return sys.modules[package_name]
    module_dir = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        package_name,
        module_dir / "__init__.py",
        submodule_search_locations=[str(module_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("generic_parser package could not be initialized")
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)
    return package


def _request_id(request) -> str:
    try:
        return request.headers.get("x-request-id") or request.headers.get("cf-ray") or str(uuid.uuid4())
    except Exception:
        return str(uuid.uuid4())


def _headers(request_id: str) -> dict[str, str]:
    return {
        **CORS_HEADERS,
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-ID": request_id,
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": CONTRACT,
        "X-GenericParser-Module-Contract": CONTRACT,
    }


def _json_response(payload: dict, request_id: str, status: int = 200):
    body = dict(payload)
    body.setdefault("request_id", request_id)
    body.setdefault("timestamp", datetime.now(UTC).isoformat())
    return Response(json.dumps(body, ensure_ascii=False), status=status, headers=_headers(request_id))


def _identity() -> dict:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": CONTRACT,
        "module_contract": CONTRACT,
        "technical_base": "0.45.1",
        "operational_reference": "0.44.6.5",
        "functional_reference": "0.44.4",
        "edge_shell": True,
        "search_behavior_changed": False,
    }


def _log(request, request_id: str, path: str, status: int, phase: str, error: str | None = None) -> None:
    try:
        record = {
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "route": path,
            "method": str(request.method),
            "origin": request.headers.get("origin"),
            "user_agent": request.headers.get("user-agent"),
            "http_status": status,
            "phase": phase,
            "error": error,
        }
        print(json.dumps({"genericparser_edge": record}, ensure_ascii=False))
    except Exception:
        pass


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        request_id = _request_id(request)
        try:
            path = urlparse(str(request.url)).path
        except Exception:
            path = "/"
        method = str(request.method).upper()

        # Preflight must never depend on FastAPI/Pydantic/search imports.
        if method == "OPTIONS":
            _log(request, request_id, path, 204, "edge_preflight")
            return Response("", status=204, headers=_headers(request_id))

        # These endpoints are intentionally dependency-free so Browser/CORS,
        # Worker routing and deployed identity can always be diagnosed.
        if method == "GET" and path == "/health":
            payload = {"status": "ok", **_identity(), "cors": True, "preflight": True, "search_ready": True}
            _log(request, request_id, path, 200, "edge_health")
            return _json_response(payload, request_id)

        if method == "GET" and path in {"/version", "/api/version"}:
            _log(request, request_id, path, 200, "edge_version")
            return _json_response({"status": "ok", **_identity()}, request_id)

        if method == "GET" and path == "/diagnostics":
            payload = {
                "status": "ok",
                "worker": _identity(),
                "checks": {
                    "edge_runtime": True,
                    "routing": True,
                    "cors": True,
                    "preflight": True,
                    "module_contract": CONTRACT,
                    "asgi_loaded": "generic_parser.cloudflare_v0451" in sys.modules,
                    "search_behavior_changed": False,
                },
                "routes": {
                    "health": "/health",
                    "version": "/version",
                    "diagnostics": "/diagnostics",
                    "search": ["/search", "/api/search", "/api/module/search", "/api/module/v1/search"],
                },
            }
            _log(request, request_id, path, 200, "edge_diagnostics")
            return _json_response(payload, request_id)

        # Import the heavier ASGI/FastAPI path only for application traffic.
        # If it fails, return a browser-readable CORS JSON error instead of a
        # network-level Load failed response.
        try:
            _load_generic_parser_package()
            from generic_parser.cloudflare_v0451 import app

            response = await asgi.fetch(app, request, self.env)
            try:
                response.headers.set("Access-Control-Allow-Origin", "*")
                response.headers.set("Access-Control-Allow-Methods", CORS_HEADERS["Access-Control-Allow-Methods"])
                response.headers.set("Access-Control-Allow-Headers", CORS_HEADERS["Access-Control-Allow-Headers"])
                response.headers.set("Access-Control-Expose-Headers", CORS_HEADERS["Access-Control-Expose-Headers"])
                response.headers.set("Access-Control-Max-Age", "86400")
                response.headers.set("X-Request-ID", request_id)
                response.headers.set("X-GenericParser-Version", VERSION)
                response.headers.set("X-GenericParser-Build", BUILD_ID)
                response.headers.set("X-GenericParser-Contract", CONTRACT)
                response.headers.set("X-GenericParser-Module-Contract", CONTRACT)
            except Exception:
                pass
            _log(request, request_id, path, int(response.status), "asgi_forward")
            return response
        except Exception as exc:
            _log(request, request_id, path, 503, "asgi_bootstrap_failed", f"{type(exc).__name__}: {exc}")
            return _json_response(
                {
                    "status": "error",
                    "detail": "GenericParser application bootstrap failed.",
                    "error_type": type(exc).__name__,
                    "phase": "asgi_bootstrap",
                    "retryable": True,
                    "worker": _identity(),
                },
                request_id,
                status=503,
            )
