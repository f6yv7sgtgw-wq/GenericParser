"""GenericParser 0.43.0 source-driven pagination.

The Free-plan packet extractor remains unchanged, but source-page transitions are
now driven by the actual Kleinanzeigen "Weiter" link returned in the HTML.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from fastapi import Request
from pydantic import Field

from . import search_service_v0427 as base

VERSION = "0.43.0"
BUILD_ID = "gp-0430-20260803-1"
API_CONTRACT = "match-v6.2-next-link-worker"

_NEXT_PATTERNS = (
    re.compile(r'<a\b[^>]*\brel=["\'][^"\']*next[^"\']*["\'][^>]*\bhref=["\']([^"\']+)', re.I),
    re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>\s*(?:<[^>]+>\s*)*Weiter(?:\s*</[^>]+>)*\s*</a>', re.I | re.S),
    re.compile(r'<a\b[^>]*\bclass=["\'][^"\']*(?:pagination-next|pagination-next-link)[^"\']*["\'][^>]*\bhref=["\']([^"\']+)', re.I),
)


class SearchRequest(base.SearchRequest):
    cursor_url: str | None = Field(default=None, max_length=2000)


def _next_url(source: str) -> str | None:
    for pattern in _NEXT_PATTERNS:
        match = pattern.search(source)
        if match:
            return urljoin(base.BASE_URL, match.group(1).replace("&amp;", "&"))
    return None


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    captured: dict[str, str] = {}
    original_source_url = base._source_url
    original_fetch_html = base._fetch_html

    def source_url(_payload: Any, source_page: int) -> str:
        if payload.cursor_url:
            return payload.cursor_url
        return original_source_url(payload, source_page)

    async def fetch_html(url: str) -> str:
        source = await original_fetch_html(url)
        captured["url"] = url
        captured["html"] = source
        return source

    base._source_url = source_url
    base._fetch_html = fetch_html
    try:
        result = await base.search_page(payload, request)
    finally:
        base._source_url = original_source_url
        base._fetch_html = original_fetch_html

    source = captured.get("html", payload.html or "")
    actual_url = captured.get("url") or payload.cursor_url
    pagination = dict(result.get("pagination") or {})
    source_cards = int(pagination.get("source_cards") or 0)
    packet_index = int(pagination.get("packet_index") or 0)
    packet_size = int(pagination.get("packet_size") or base.PACKET_SIZE)
    selected_count = int((result.get("summary") or {}).get("fetched_listings") or 0)
    source_page_finished = min(source_cards, packet_index * packet_size + selected_count) >= source_cards
    discovered_next = _next_url(source) if source_page_finished else actual_url

    complete = False
    stop_reason = "work_packet_complete"
    if source_cards == 0:
        complete, stop_reason = True, "empty_page_verified"
    elif source_page_finished and not discovered_next:
        complete, stop_reason = True, "next_link_missing"

    pagination.update({
        "complete": complete,
        "partial": not complete,
        "continuation_available": not complete,
        "next_page": None if complete else int(payload.page) + 1,
        "stop_reason": stop_reason,
        "cursor_url": discovered_next,
        "requested_cursor_url": payload.cursor_url,
        "actual_source_url": actual_url,
        "next_link_found": bool(discovered_next),
        "next_link_strategy": "source_html_weiter_link",
        "reported_total_is_diagnostic_only": True,
        "reported_total_stop_disabled": True,
        "worker_unit": "free-cpu-work-packet+source-next-link",
    })
    result["pagination"] = pagination
    result["generated_urls"] = [actual_url] if actual_url else result.get("generated_urls", [])
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": "free-cpu-work-packet+source-next-link",
    }
    result["consistency"] = {
        **(result.get("consistency") or {}),
        "reported_total_not_used_as_stop": True,
        "source_next_link_checked": source_page_finished,
        "next_link_state_consistent": complete or bool(discovered_next),
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
