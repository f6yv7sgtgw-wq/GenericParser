"""GenericParser 0.40 – resumable production page worker."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from . import cloudflare_v039 as page_worker

VERSION = "0.40.0"
page_worker.VERSION = VERSION
app = page_worker.app

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_page_error(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a Cloudflare HTML error page to the browser.

    A single failed source page is retryable. The browser persists its cursor and
    retries the same page with exponential backoff.
    """
    logger.exception("Unhandled page-worker error", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Temporärer Seitenfehler. Die Seite kann erneut versucht werden.",
            "retryable": True,
            "error_type": type(exc).__name__,
            "worker": {
                "version": VERSION,
                "worker_unit": "one-page",
                "api_contract": "match-v7-resumable-page-worker",
            },
        },
        headers={"Retry-After": "15"},
    )


@app.get("/api/runtime")
async def runtime() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": VERSION,
        "worker_unit": "one-page",
        "resumable": True,
        "structured_errors": True,
    }


__all__ = ["app"]
