"""GenericParser 0.42.3 pagination guard over the app-free one-page service."""
from __future__ import annotations

from typing import Any

from fastapi import Request

from . import search_service_v0422 as base

VERSION = "0.42.3"
BUILD_ID = "gp-0423-20260802-1"
API_CONTRACT = "match-v6.1-page-worker"
HTML_PAGE_SIZE = 25
MOBILE_PAGE_SIZE = base.MOBILE_PAGE_SIZE
SearchRequest = base.SearchRequest


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await base.search_page(payload, request)
    pagination = dict(result.get("pagination") or {})
    summary = dict(result.get("summary") or {})
    source = str(pagination.get("source") or payload.source)
    count = int(summary.get("fetched_listings") or 0)
    reported_total_raw = summary.get("reported_total")
    reported_total = int(reported_total_raw) if reported_total_raw is not None else None
    page_size = MOBILE_PAGE_SIZE if source == "mobile-api" else HTML_PAGE_SIZE
    covered_until = int(payload.page) * page_size + count

    complete = bool(pagination.get("complete"))
    stop_reason = str(pagination.get("stop_reason") or "page_complete")

    if payload.mode == "html":
        complete, stop_reason = True, "html_mode"
    elif count == 0:
        complete, stop_reason = True, "empty_page_verified"
    elif reported_total is not None and covered_until >= reported_total:
        complete, stop_reason = True, "reported_total_reached"
    elif source == "html-fallback" and count < HTML_PAGE_SIZE:
        complete, stop_reason = True, "short_html_page"
    elif source == "mobile-api" and count < MOBILE_PAGE_SIZE:
        complete, stop_reason = True, "short_mobile_page"

    pagination.update({
        "complete": complete,
        "partial": not complete,
        "continuation_available": not complete,
        "next_page": None if complete else int(payload.page) + 1,
        "stop_reason": stop_reason,
        "page_size_assumed": page_size,
        "covered_until": covered_until,
        "reported_total_guard": reported_total is not None,
        "worker_unit": "one-page-service+pagination-guard",
    })
    result["pagination"] = pagination
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": "app-free-one-page-service+pagination-guard",
    }
    result["consistency"] = {
        **(result.get("consistency") or {}),
        "pagination_guard_ok": not complete or pagination.get("next_page") is None,
        "covered_until": covered_until,
        "reported_total": reported_total,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
