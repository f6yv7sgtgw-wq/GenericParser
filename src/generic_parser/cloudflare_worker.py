"""Cloudflare-Python-Worker entrypoint for GenericParser 0.45.2 Build 6.

Build 6 keeps the proven Build 5 Worker-edge CORS preflight handler and the
0.45.0 search runtime unchanged. Evercade payload compatibility is implemented
inside the ASGI alias /api/module/search only.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import asgi
from workers import Response, WorkerEntrypoint


CORS_ALLOW_ORIGIN = "*"
CORS_ALLOW_METHODS = "GET,HEAD,POST,OPTIONS"
CORS_ALLOW_HEADERS = (
    "Accept,Content-Type,X-Generic-Parser-Contract,X-Request-Id,"
    "X-GenericParser-Contract,X-GenericParser-Token,"
    "X-GenericParser-Debug,X-GenericParser-Tests"
)
CORS_MAX_AGE = "86400"


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


def _header(request, name: str) -> str | None:
    """Read a Fetch API header without depending on one headers wrapper shape."""
    try:
        value = request.headers.get(name)
        if value is not None:
            return str(value)
    except Exception:
        pass
    try:
        return str(request.headers[name]) if name in request.headers else None
    except Exception:
        return None


def _preflight_response(request) -> Response:
    """Answer browser CORS preflight at the Worker edge, before ASGI."""
    requested_headers = _header(request, "Access-Control-Request-Headers")
    headers = {
        "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
        "Access-Control-Allow-Methods": CORS_ALLOW_METHODS,
        "Access-Control-Allow-Headers": requested_headers or CORS_ALLOW_HEADERS,
        "Access-Control-Max-Age": CORS_MAX_AGE,
        "Vary": "Origin, Access-Control-Request-Method, Access-Control-Request-Headers",
        "Cache-Control": "no-store",
        "X-GenericParser-CORS-Layer": "worker-edge-build6",
    }
    return Response(None, status=204, headers=headers)


_load_generic_parser_package()
from generic_parser.cloudflare_v0452 import app  # noqa: E402


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if str(request.method).upper() == "OPTIONS":
            return _preflight_response(request)
        return await asgi.fetch(app, request, self.env)
