"""GenericParser 0.41.1 – deployment handshake on stable page-worker core."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse

from . import cloudflare_v039 as page_worker

VERSION = "0.41.1"
BUILD_ID = "gp-0411-20260802-1"
BUILD_REVISION = BUILD_ID
API_CONTRACT = "match-v6.1-page-worker"

# Use the proven one-page worker directly. 0.41 resource middleware is
# intentionally not imported because it caused plain-text 500 responses.
page_worker.VERSION = VERSION
app = page_worker.app


@app.middleware("http")
async def build_identity_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Any]],
):
    """Attach the same build identity to every reachable API response."""
    try:
        response = await call_next(request)
    except Exception as exc:
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Interner Worker-Fehler wurde kontrolliert abgefangen.",
                "retryable": False,
                "error_type": type(exc).__name__,
                "phase": "asgi_request",
                "worker": {
                    "version": VERSION,
                    "build_id": BUILD_ID,
                    "build_revision": BUILD_REVISION,
                    "api_contract": API_CONTRACT,
                },
            },
        )
    response.headers["X-GenericParser-Version"] = VERSION
    response.headers["X-GenericParser-Build"] = BUILD_ID
    response.headers["X-GenericParser-Commit"] = BUILD_REVISION
    response.headers["X-GenericParser-Contract"] = API_CONTRACT
    return response


@app.get("/api/version")
async def api_version() -> dict[str, Any]:
    """Cheap readiness endpoint used before enabling live search."""
    return {
        "status": "ok",
        "version": VERSION,
        "build_id": BUILD_ID,
        "build_revision": BUILD_REVISION,
        "api_contract": API_CONTRACT,
        "worker_unit": "one-page",
        "search_ready": True,
    }


@app.get("/api/resource-status")
async def resource_status_0411() -> dict[str, Any]:
    """Explicitly describe metrics available in the stable release."""
    return {
        "status": "ok",
        "version": VERSION,
        "build_id": BUILD_ID,
        "build_revision": BUILD_REVISION,
        "resource_diagnostics": "disabled_for_stability",
        "memory": "runtime_not_exposed",
    }


__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
