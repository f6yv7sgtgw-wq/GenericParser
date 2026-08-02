"""GenericParser 0.40.9 – guarded HTML fallback with server phase diagnostics."""
from __future__ import annotations

import time
import traceback
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from . import cloudflare_v039 as page_worker
from .sources.kleinanzeigen import KleinanzeigenBlockedError, KleinanzeigenLayoutError

VERSION = "0.40.9"
page_worker.VERSION = VERSION
app = page_worker.app

_original_html_page = page_worker._html_page


class HtmlFallbackPhaseError(RuntimeError):
    def __init__(self, phase: str, original: BaseException, *, target_url: str | None = None):
        super().__init__(str(original) or type(original).__name__)
        self.phase = phase
        self.original = original
        self.target_url = target_url


async def _guarded_html_page(payload: Any, url: str):
    phase = "html_page_url_build"
    target_url: str | None = None
    started = time.perf_counter()
    try:
        target_url = page_worker.dynamic._html_page_url(url, payload.page)
        phase = "html_fetch"
        page = await page_worker.core.fetch_search_page(target_url)
        phase = "html_parse"
        parsed = page_worker.core.CloudflarePageParser().parse(page, source_query=payload.query)
        phase = "html_total_extract"
        reported_total = page_worker._html_reported_total(page.text)
        return parsed, reported_total
    except (KleinanzeigenBlockedError, KleinanzeigenLayoutError, httpx.RequestError) as exc:
        raise HtmlFallbackPhaseError(phase, exc, target_url=target_url) from exc
    except Exception as exc:
        raise HtmlFallbackPhaseError(phase, exc, target_url=target_url) from exc
    finally:
        _ = time.perf_counter() - started


page_worker._html_page = _guarded_html_page


@app.exception_handler(HtmlFallbackPhaseError)
async def html_fallback_error_handler(request: Request, exc: HtmlFallbackPhaseError) -> JSONResponse:
    ray_id = request.headers.get("cf-ray")
    status = 429 if isinstance(exc.original, KleinanzeigenBlockedError) else 502
    return JSONResponse(
        status_code=status,
        content={
            "detail": f"HTML-Fallback fehlgeschlagen in Phase {exc.phase}: {exc}",
            "retryable": status in {429, 502, 503, 504},
            "error_type": type(exc.original).__name__,
            "phase": exc.phase,
            "target_url": exc.target_url,
            "ray_id": ray_id,
            "traceback": traceback.format_exception_only(type(exc.original), exc.original)[-1].strip(),
            "worker": {"version": VERSION, "server_phase_guard": True},
        },
        headers={
            "X-GenericParser-Version": VERSION,
            "X-GenericParser-Phase": exc.phase,
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    ray_id = request.headers.get("cf-ray")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Interner Worker-Fehler wurde kontrolliert abgefangen.",
            "retryable": False,
            "error_type": type(exc).__name__,
            "phase": "asgi_unhandled_exception",
            "ray_id": ray_id,
            "traceback": traceback.format_exception_only(type(exc), exc)[-1].strip(),
            "worker": {"version": VERSION, "server_phase_guard": True},
        },
        headers={
            "X-GenericParser-Version": VERSION,
            "X-GenericParser-Phase": "asgi_unhandled_exception",
        },
    )


__all__ = ["app"]
