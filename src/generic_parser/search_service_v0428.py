"""GenericParser 0.42.8 pagination-end guard for Free-plan work packets.

The reported result total is diagnostic only. It must never terminate the run,
because sponsored/hidden cards and source-page composition make it unsuitable
as a consumed-card counter. Natural completion is determined only by an empty
source page or a short final source page. Repeated-ID protection remains in the
browser controller.
"""
from __future__ import annotations

from typing import Any
from fastapi import Request

from . import search_service_v0427 as base

VERSION = "0.42.8"
BUILD_ID = "gp-0428-20260803-1"
API_CONTRACT = "match-v6.1-page-worker"
SearchRequest = base.SearchRequest


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await base.search_page(payload, request)
    pagination = dict(result.get("pagination") or {})
    summary = dict(result.get("summary") or {})

    source_cards = int(pagination.get("source_cards") or 0)
    source_page = int(pagination.get("source_page") or 0)
    packet_index = int(pagination.get("packet_index") or 0)
    packet_size = int(pagination.get("packet_size") or base.PACKET_SIZE)
    consumed_on_source_page = min(source_cards, packet_index * packet_size + int(summary.get("fetched_listings") or 0))
    source_page_finished = consumed_on_source_page >= source_cards

    complete = False
    stop_reason = "work_packet_complete"
    if source_cards == 0:
        complete, stop_reason = True, "empty_page_verified"
    elif source_page_finished and source_cards < base.SOURCE_PAGE_SIZE:
        complete, stop_reason = True, "short_source_page"

    pagination.update({
        "complete": complete,
        "partial": not complete,
        "continuation_available": not complete,
        "next_page": None if complete else int(payload.page) + 1,
        "stop_reason": stop_reason,
        "reported_total_is_diagnostic_only": True,
        "reported_total_stop_disabled": True,
        "natural_end_guard": "empty_or_short_source_page",
        "source_page": source_page,
        "worker_unit": "free-cpu-work-packet+natural-end-guard",
    })
    result["pagination"] = pagination
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": "free-cpu-work-packet+natural-end-guard",
    }
    result["consistency"] = {
        **(result.get("consistency") or {}),
        "reported_total_not_used_as_stop": True,
        "natural_end_guard_ok": complete or pagination.get("next_page") is not None,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
