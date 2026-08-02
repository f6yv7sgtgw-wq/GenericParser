"""GenericParser 0.42.5 search service using the native Workers Fetch API via FFI."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from . import search_service_v0422 as base
from . import search_service_v0423 as pagination
from .build_identity_v0425 import API_CONTRACT, BUILD_ID, VERSION

SearchRequest = base.SearchRequest
MOBILE_PAGE_SIZE = base.MOBILE_PAGE_SIZE


@dataclass(frozen=True)
class NativeResponse:
    status: int
    url: str
    text: str
    content_type: str | None
    cf_error_type: str | None
    cf_ray: str | None


async def _native_fetch(url: str, headers: dict[str, str], *, timeout_seconds: float = 20.0) -> NativeResponse:
    """Use the Cloudflare Workers Fetch API directly.

    Python Workers expose JavaScript runtime APIs through the FFI. A local
    httpx fallback is retained only for non-Workers tests.
    """
    try:
        from js import fetch as workers_fetch  # type: ignore
        from pyodide.ffi import to_js  # type: ignore
    except ImportError:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
        return NativeResponse(
            status=response.status_code,
            url=str(response.url),
            text=response.text,
            content_type=response.headers.get("content-type"),
            cf_error_type=response.headers.get("cf-error-type"),
            cf_ray=response.headers.get("cf-ray"),
        )

    options = to_js({"method": "GET", "headers": headers, "redirect": "follow"}, dict_converter=None)
    response = await asyncio.wait_for(workers_fetch(url, options), timeout=timeout_seconds)
    text = str(await asyncio.wait_for(response.text(), timeout=timeout_seconds))
    return NativeResponse(
        status=int(response.status),
        url=str(response.url),
        text=text,
        content_type=str(response.headers.get("content-type") or "") or None,
        cf_error_type=str(response.headers.get("cf-error-type") or "") or None,
        cf_ray=str(response.headers.get("cf-ray") or "") or None,
    )


async def _mobile_page_native(payload: SearchRequest) -> tuple[Any, int | None, dict[str, Any]]:
    core = base.core
    headers = {
        "Authorization": f"Basic {core.MOBILE_API_BASIC_AUTH}",
        "User-Agent": "okhttp/4.10.0",
        "Accept": "application/json",
        "X-EBAYK-APP": "genericparser-cloudflare",
    }
    request_url = core._mobile_url(payload, page=payload.page, size=MOBILE_PAGE_SIZE)
    response = await _native_fetch(request_url, headers)
    diagnostics = {
        "transport": "workers-fetch-ffi",
        "request_url": request_url,
        "http_status": response.status,
        "response_bytes": len(response.text.encode("utf-8")),
        "content_type": response.content_type,
        "cf_error_type": response.cf_error_type,
        "cf_ray": response.cf_ray,
    }
    if response.status in {401, 403, 429}:
        raise base.KleinanzeigenBlockedError(f"Kleinanzeigen-App-API verweigert den Zugriff ({response.status})")
    if response.status >= 400:
        raise HTTPException(status_code=502, detail=f"Kleinanzeigen-App-API antwortet mit HTTP {response.status}")
    data = json.loads(response.text)
    parsed = core._parse_mobile(data, payload.query, page=payload.page)
    diagnostics.update(raw_cards=parsed.diagnostics.cards_found, parsed_listings=len(parsed.listings), valid_listings=base._valid_count(parsed))
    return parsed, base.scope._extract_reported_total(data), diagnostics


async def _html_page_native(payload: SearchRequest, url: str) -> tuple[Any, int | None]:
    page_url = base.dynamic._html_page_url(url, payload.page)
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
        "Cache-Control": "no-cache",
    }
    response = await _native_fetch(page_url, headers)
    if response.status in {403, 429} or base.core.KleinanzeigenHttpClient._looks_blocked(response.text):
        raise base.KleinanzeigenBlockedError(f"Kleinanzeigen blockiert den Abruf ({response.status})")
    if response.status >= 400:
        detail = {
            "message": f"Kleinanzeigen antwortet mit HTTP {response.status}",
            "transport": "workers-fetch-ffi",
            "cf_error_type": response.cf_error_type,
            "cf_ray": response.cf_ray,
        }
        raise HTTPException(status_code=502, detail=detail)
    page = base.core.FetchedPage(page_url, response.url, response.status, response.text)
    parsed = base.core.CloudflarePageParser().parse(page, source_query=payload.query)
    return parsed, base._html_reported_total(response.text)


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    original_mobile = base._mobile_page
    original_html = base._html_page
    base._mobile_page = _mobile_page_native
    base._html_page = _html_page_native
    try:
        result = await pagination.search_page(payload, request)
    finally:
        base._mobile_page = original_mobile
        base._html_page = original_html

    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "transport": "workers-fetch-ffi",
        "worker_unit": "app-free-one-page-service+native-fetch+pagination-guard",
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
