"""GenericParser 0.43.4 coverage-evidence search service.

Keeps the proven 0.43.3 search flow unchanged and adds bounded diagnostics that
explain the gap between Kleinanzeigen's reported total and extractable cards.
No raw HTML is persisted or returned.
"""
from __future__ import annotations

import re
from typing import Any
from fastapi import Request

from . import search_service_v0430 as flow
from .build_identity_v0434 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = flow.SearchRequest

_ARTICLE_ANY_RE = re.compile(r"<article\b", re.I)
_DATA_ADID_RE = re.compile(r"<article\b[^>]*\bdata-adid=[\"']([^\"']+)", re.I)
_ANZEIGE_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']*/s-anzeige/[^\"']+)", re.I)
_ADID_ANY_RE = re.compile(r"\bdata-adid=[\"']([^\"']+)", re.I)


def _next_link_evidence(source: str) -> dict[str, Any]:
    matches: list[dict[str, str]] = []
    names = ("rel_next", "text_weiter", "pagination_class")
    for name, pattern in zip(names, flow._NEXT_PATTERNS):
        match = pattern.search(source)
        if match:
            matches.append({"strategy": name, "href": match.group(1).replace("&amp;", "&")[:500]})
    return {
        "candidate_count": len(matches),
        "candidates": matches,
        "selected_strategy": matches[0]["strategy"] if matches else None,
        "selected_href": matches[0]["href"] if matches else None,
    }


def _card_evidence(source: str, result: dict[str, Any], payload: SearchRequest) -> dict[str, Any]:
    pagination = result.get("pagination") or {}
    summary = result.get("summary") or {}
    ranges = flow.base._card_ranges(source)
    packet_index = int(pagination.get("packet_index") or 0)
    packet_size = int(pagination.get("packet_size") or flow.base.PACKET_SIZE)
    start_index = packet_index * packet_size
    selected = ranges[start_index:start_index + packet_size]

    malformed: list[dict[str, Any]] = []
    for listing_id, start, end in selected:
        card = source[start:end]
        link = flow.base._LINK_RE.search(card)
        if not link:
            malformed.append({"id": listing_id, "reason": "anzeige_link_missing"})
            continue
        title = flow.base._text(link.group(2))
        if not title:
            malformed.append({"id": listing_id, "reason": "title_empty"})

    article_ids = _DATA_ADID_RE.findall(source)
    any_adids = _ADID_ANY_RE.findall(source)
    links = _ANZEIGE_LINK_RE.findall(source)
    unique_article_ids = list(dict.fromkeys(article_ids))
    unique_any_adids = list(dict.fromkeys(any_adids))
    unique_links = list(dict.fromkeys(links))

    returned_ids = [str(item.get("id")) for item in result.get("listings") or [] if item.get("id") is not None]
    selected_ids = [listing_id for listing_id, _, _ in selected]
    return {
        "schema": "coverage-evidence-v1",
        "source_page": pagination.get("source_page"),
        "packet_index": packet_index,
        "html_bytes": len(source.encode("utf-8")),
        "html_article_tags": len(_ARTICLE_ANY_RE.findall(source)),
        "html_article_data_adid": len(article_ids),
        "html_unique_article_ids": len(unique_article_ids),
        "html_all_data_adid": len(any_adids),
        "html_unique_all_adids": len(unique_any_adids),
        "html_s_anzeige_links": len(links),
        "html_unique_s_anzeige_links": len(unique_links),
        "range_count": len(ranges),
        "selected_range_count": len(selected),
        "selected_ids": selected_ids,
        "returned_ids": returned_ids,
        "extracted_count": int(summary.get("fetched_listings") or 0),
        "visible_count": int(summary.get("visible_listings") or 0),
        "hidden_count": int(summary.get("hidden_by_filter") or 0),
        "malformed_count": len(malformed),
        "malformed": malformed,
        "reported_total": summary.get("reported_total"),
        "next_link": _next_link_evidence(source),
        "actual_source_url": pagination.get("actual_source_url"),
        "requested_cursor_url": pagination.get("requested_cursor_url"),
        "stop_reason": pagination.get("stop_reason"),
        "no_raw_html_persisted": True,
    }


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    captured: dict[str, str] = {}
    original_fetch = flow.base._fetch_html

    async def capture_fetch(url: str) -> str:
        source = await original_fetch(url)
        captured["url"] = url
        captured["html"] = source
        return source

    flow.base._fetch_html = capture_fetch
    try:
        result = await flow.search_page(payload, request)
    finally:
        flow.base._fetch_html = original_fetch

    source = captured.get("html", payload.html or "")
    result["coverage_diagnostics"] = _card_evidence(source, result, payload)
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "coverage_evidence": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
