"""GenericParser 0.42.9 coverage diagnostics for Free-plan work packets."""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v0428 as base

VERSION = "0.42.9"
BUILD_ID = "gp-0429-20260803-1"
API_CONTRACT = "match-v6.1-page-worker"
SearchRequest = base.SearchRequest

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await base.search_page(payload, request)
    pagination = dict(result.get("pagination") or {})
    summary = dict(result.get("summary") or {})
    reported = pagination.get("reported_total")
    source_cards = int(pagination.get("source_cards") or 0)
    fetched = int(summary.get("fetched_listings") or 0)
    malformed = int(summary.get("malformed_rejected") or 0)
    packet_index = int(pagination.get("packet_index") or 0)
    packet_size = int(pagination.get("packet_size") or 7)
    selected_estimate = min(packet_size, max(0, source_cards - packet_index * packet_size))
    skipped = max(0, selected_estimate - fetched)
    coverage = {
        "reported_total": reported,
        "source_cards": source_cards,
        "selected_cards": selected_estimate,
        "extracted_cards": fetched,
        "skipped_cards": skipped,
        "malformed_cards": malformed,
        "packet_coverage_percent": round((fetched / selected_estimate) * 100, 1) if selected_estimate else 100.0,
        "reported_total_gap_is_diagnostic": True,
        "layout_probe": "article[data-adid]",
    }
    pagination["coverage_diagnostics"] = coverage
    pagination["worker_unit"] = "free-cpu-work-packet+natural-end+coverage-diagnostics"
    summary["coverage_diagnostics"] = coverage
    result["pagination"] = pagination
    result["summary"] = summary
    result["worker"] = {**(result.get("worker") or {}), "version": VERSION, "build_id": BUILD_ID, "api_contract": API_CONTRACT, "worker_unit": "free-cpu-work-packet+natural-end+coverage-diagnostics", "coverage_diagnostics": True}
    result["consistency"] = {**(result.get("consistency") or {}), "coverage_accounted": fetched + skipped == selected_estimate}
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
