"""GenericParser 0.41 – lightweight per-request resource diagnostics.

Cloudflare does not expose a reliable live heap counter to the Python worker.
This release therefore records wall/process timings and payload sizes without
inventing memory values.
"""
from __future__ import annotations

import contextvars
import json
import time
import traceback
from typing import Any, Awaitable, Callable

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from . import cloudflare_v039 as page_worker
from .sources.kleinanzeigen import KleinanzeigenBlockedError, KleinanzeigenLayoutError

VERSION = "0.41.0"
page_worker.VERSION = VERSION
app = page_worker.app

_metrics: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("gp041_metrics", default={})
_original_html_page = page_worker._html_page
_original_mobile_page = page_worker._mobile_page


def _ms(start: float) -> int:
    return max(0, round((time.perf_counter() - start) * 1000))


def _merge(**values: Any) -> None:
    current = dict(_metrics.get())
    current.update(values)
    _metrics.set(current)


async def _timed_html_page(payload: Any, url: str):
    total_started = time.perf_counter()
    phase = "html_url_build"
    target_url: str | None = None
    try:
        url_started = time.perf_counter()
        target_url = page_worker.dynamic._html_page_url(url, payload.page)
        _merge(html_url_ms=_ms(url_started), target_url=target_url, source="html-fallback")

        phase = "html_fetch"
        fetch_started = time.perf_counter()
        page = await page_worker.core.fetch_search_page(target_url)
        _merge(
            html_fetch_ms=_ms(fetch_started),
            upstream_status=page.status_code,
            html_bytes=len(page.text.encode("utf-8", errors="replace")),
        )

        phase = "html_parse"
        parse_started = time.perf_counter()
        parsed = page_worker.core.CloudflarePageParser().parse(page, source_query=payload.query)
        _merge(html_parse_ms=_ms(parse_started), parsed_cards=len(parsed.listings))

        phase = "html_total_extract"
        total_extract_started = time.perf_counter()
        reported_total = page_worker._html_reported_total(page.text)
        _merge(html_total_extract_ms=_ms(total_extract_started), reported_total=reported_total)
        return parsed, reported_total
    except Exception as exc:
        _merge(error_phase=phase, target_url=target_url, error_type=type(exc).__name__)
        raise
    finally:
        _merge(html_total_ms=_ms(total_started))


async def _timed_mobile_page(payload: Any):
    started = time.perf_counter()
    try:
        result = await _original_mobile_page(payload)
        parsed, reported_total, diagnostics = result
        _merge(
            source="mobile-api",
            mobile_total_ms=_ms(started),
            mobile_response_bytes=diagnostics.get("response_bytes"),
            mobile_cards=diagnostics.get("parsed_listings"),
            reported_total=reported_total,
        )
        return result
    except Exception as exc:
        _merge(error_phase="mobile_request_or_parse", error_type=type(exc).__name__, mobile_total_ms=_ms(started))
        raise


page_worker._html_page = _timed_html_page
page_worker._mobile_page = _timed_mobile_page


@app.middleware("http")
async def resource_diagnostics(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    token = _metrics.set({
        "version": VERSION,
        "memory_bytes": None,
        "memory_note": "runtime_not_exposed",
    })
    try:
        response = await call_next(request)
        values = dict(_metrics.get())
        values["request_wall_ms"] = _ms(wall_started)
        values["process_cpu_ms"] = max(0, round((time.process_time() - cpu_started) * 1000))
        encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        response.headers["X-GenericParser-Version"] = VERSION
        response.headers["X-GenericParser-Resources"] = encoded[:6000]
        response.headers["X-GenericParser-Wall-Ms"] = str(values["request_wall_ms"])
        response.headers["X-GenericParser-CPU-Ms"] = str(values["process_cpu_ms"])
        return response
    except Exception as exc:
        values = dict(_metrics.get())
        values.update({
            "request_wall_ms": _ms(wall_started),
            "process_cpu_ms": max(0, round((time.process_time() - cpu_started) * 1000)),
            "error_type": type(exc).__name__,
        })
        ray_id = request.headers.get("cf-ray")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Worker-Fehler wurde von der 0.41-Ressourcendiagnose abgefangen.",
                "retryable": False,
                "error_type": type(exc).__name__,
                "phase": values.get("error_phase", "asgi_request"),
                "ray_id": ray_id,
                "target_url": values.get("target_url"),
                "resources": values,
                "traceback": traceback.format_exception_only(type(exc), exc)[-1].strip(),
                "worker": {"version": VERSION, "resource_diagnostics": True},
            },
            headers={
                "X-GenericParser-Version": VERSION,
                "X-GenericParser-Resources": json.dumps(values, ensure_ascii=False, separators=(",", ":"))[:6000],
            },
        )
    finally:
        _metrics.reset(token)


@app.get("/api/resource-status")
async def resource_status() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": VERSION,
        "measured": [
            "request_wall_ms",
            "process_cpu_ms",
            "html_url_ms",
            "html_fetch_ms",
            "html_parse_ms",
            "html_total_extract_ms",
            "html_total_ms",
            "html_bytes",
            "mobile_total_ms",
            "mobile_response_bytes",
        ],
        "not_available": ["live_heap_bytes", "garbage_collection_count"],
    }


__all__ = ["app"]
