"""GenericParser 0.40.5 – phase-aware diagnostic page worker."""

from __future__ import annotations

import contextvars
import time
import traceback
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse

from . import cloudflare_v039 as page_worker

VERSION = "0.40.5"
page_worker.VERSION = VERSION
app = page_worker.app

_phase: contextvars.ContextVar[str] = contextvars.ContextVar("gp_phase", default="request_received")
_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("gp_context", default={})


def _set_phase(name: str, **values: Any) -> None:
    _phase.set(name)
    current = dict(_context.get())
    current.update(values)
    _context.set(current)


_original_mobile_page = page_worker._mobile_page
_original_html_page = page_worker._html_page


async def _diagnostic_mobile_page(payload: Any):
    _set_phase("mobile_url_build", query=payload.query, page=payload.page, source="mobile-api")
    try:
        _set_phase("mobile_http_request")
        result = await _original_mobile_page(payload)
        _set_phase("mobile_response_parsed")
        return result
    except Exception:
        _set_phase("mobile_failed")
        raise


async def _diagnostic_html_page(payload: Any, url: str):
    _set_phase("html_url_build", query=payload.query, page=payload.page, source="html-fallback", target_url=url)
    try:
        _set_phase("html_http_request")
        result = await _original_html_page(payload, url)
        _set_phase("html_response_parsed")
        return result
    except Exception:
        _set_phase("html_failed")
        raise


page_worker._mobile_page = _diagnostic_mobile_page
page_worker._html_page = _diagnostic_html_page


@app.middleware("http")
async def diagnostic_context(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
    """Attach phase metadata without consuming the request body.

    Query and page are captured inside the instrumented page functions after
    FastAPI has decoded and validated the request payload.
    """
    started = time.perf_counter()
    token_phase = _phase.set("request_received")
    token_context = _context.set({"path": request.url.path, "method": request.method})
    try:
        response = await call_next(request)
        response.headers["X-GenericParser-Version"] = VERSION
        response.headers["X-GenericParser-Phase"] = _phase.get()
        response.headers["X-GenericParser-Elapsed-Ms"] = str(round((time.perf_counter() - started) * 1000))
        return response
    except Exception as exc:
        elapsed = round((time.perf_counter() - started) * 1000)
        context = dict(_context.get())
        ray_id = request.headers.get("cf-ray")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Worker-Diagnose: Ausnahme in Phase {_phase.get()}.",
                "retryable": False,
                "error_type": type(exc).__name__,
                "phase": _phase.get(),
                "query": context.get("query"),
                "page": context.get("page"),
                "source": context.get("source"),
                "target_url": context.get("target_url"),
                "elapsed_ms": elapsed,
                "ray_id": ray_id,
                "traceback": traceback.format_exc(limit=8),
                "worker": {"version": VERSION, "diagnostic_build": True},
            },
            headers={
                "X-GenericParser-Version": VERSION,
                "X-GenericParser-Phase": _phase.get(),
                "X-GenericParser-Elapsed-Ms": str(elapsed),
            },
        )
    finally:
        _phase.reset(token_phase)
        _context.reset(token_context)


@app.get("/api/diagnostic-runtime")
async def diagnostic_runtime() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": VERSION,
        "diagnostic_build": True,
        "phases": [
            "request_received",
            "mobile_url_build",
            "mobile_http_request",
            "mobile_response_parsed",
            "html_url_build",
            "html_http_request",
            "html_response_parsed",
        ],
    }


__all__ = ["app"]
