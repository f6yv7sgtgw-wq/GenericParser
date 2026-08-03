"""GenericParser 0.43.5 bounded title-extraction evidence.

Keeps the proven 0.43.3 search state machine and 0.43.4 coverage counters.
For malformed cards only, it returns a bounded structural excerpt and candidate
title fields. Full source HTML is never persisted or returned.
"""
from __future__ import annotations

import html as html_lib
import re
from typing import Any
from fastapi import Request

from . import search_service_v0430 as flow
from .build_identity_v0435 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = flow.SearchRequest

_ARTICLE_ANY_RE = re.compile(r"<article\b", re.I)
_DATA_ADID_RE = re.compile(r"<article\b[^>]*\bdata-adid=[\"']([^\"']+)", re.I)
_ANZEIGE_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']*/s-anzeige/[^\"']+)", re.I)
_ADID_ANY_RE = re.compile(r"\bdata-adid=[\"']([^\"']+)", re.I)
_OPEN_ARTICLE_RE = re.compile(r"<article\b([^>]*)>", re.I | re.S)
_FIRST_ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
_ATTR_RE_TEMPLATE = r"\b%s\s*=\s*[\"']([^\"']*)[\"']"
_HEADING_RE = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.I | re.S)
_SCRIPT_STYLE_RE = re.compile(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", re.I | re.S)
_SPACE_RE = re.compile(r"\s+")


def _attr(fragment: str, name: str) -> str | None:
    match = re.search(_ATTR_RE_TEMPLATE % re.escape(name), fragment, re.I | re.S)
    return html_lib.unescape(match.group(1)).strip() if match else None


def _plain(fragment: str, limit: int = 500) -> str:
    return flow.base._text(fragment)[:limit]


def _bounded_excerpt(card: str, limit: int = 800) -> str:
    cleaned = _SCRIPT_STYLE_RE.sub(" ", card)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    return cleaned[:limit]


def _title_evidence(listing_id: str, card: str, reason: str) -> dict[str, Any]:
    article_match = _OPEN_ARTICLE_RE.search(card)
    article_attrs = article_match.group(1) if article_match else ""
    anchor_match = _FIRST_ANCHOR_RE.search(card)
    anchor_attrs = anchor_match.group(1) if anchor_match else ""
    anchor_body = anchor_match.group(2) if anchor_match else ""
    headings = [
        {"tag": tag.lower(), "text": _plain(body, 300)}
        for tag, body in _HEADING_RE.findall(card)[:4]
    ]
    aria_labels = [
        html_lib.unescape(value).strip()[:300]
        for value in re.findall(r"\baria-label\s*=\s*[\"']([^\"']*)[\"']", card, re.I)
        if value.strip()
    ][:6]
    title_attrs = [
        html_lib.unescape(value).strip()[:300]
        for value in re.findall(r"\btitle\s*=\s*[\"']([^\"']*)[\"']", card, re.I)
        if value.strip()
    ][:6]
    return {
        "id": listing_id,
        "reason": reason,
        "article_class": _attr(article_attrs, "class"),
        "article_role": _attr(article_attrs, "role"),
        "first_anchor_href": _attr(anchor_attrs, "href"),
        "first_anchor_class": _attr(anchor_attrs, "class"),
        "first_anchor_aria_label": _attr(anchor_attrs, "aria-label"),
        "first_anchor_title": _attr(anchor_attrs, "title"),
        "first_anchor_text": _plain(anchor_body, 400),
        "headings": headings,
        "aria_labels": aria_labels,
        "title_attributes": title_attrs,
        "article_excerpt": _bounded_excerpt(card),
        "excerpt_chars": min(len(_SPACE_RE.sub(" ", _SCRIPT_STYLE_RE.sub(" ", card)).strip()), 800),
        "bounded": True,
    }


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


def _card_evidence(source: str, result: dict[str, Any]) -> dict[str, Any]:
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
            malformed.append(_title_evidence(listing_id, card, "anzeige_link_missing"))
            continue
        title = flow.base._text(link.group(2))
        if not title:
            malformed.append(_title_evidence(listing_id, card, "title_empty"))

    article_ids = _DATA_ADID_RE.findall(source)
    any_adids = _ADID_ANY_RE.findall(source)
    links = _ANZEIGE_LINK_RE.findall(source)
    returned_ids = [str(item.get("id")) for item in result.get("listings") or [] if item.get("id") is not None]
    selected_ids = [listing_id for listing_id, _, _ in selected]
    return {
        "schema": "title-evidence-v1",
        "source_page": pagination.get("source_page"),
        "packet_index": packet_index,
        "html_bytes": len(source.encode("utf-8")),
        "html_article_tags": len(_ARTICLE_ANY_RE.findall(source)),
        "html_article_data_adid": len(article_ids),
        "html_unique_article_ids": len(dict.fromkeys(article_ids)),
        "html_all_data_adid": len(any_adids),
        "html_unique_all_adids": len(dict.fromkeys(any_adids)),
        "html_s_anzeige_links": len(links),
        "html_unique_s_anzeige_links": len(dict.fromkeys(links)),
        "range_count": len(ranges),
        "selected_range_count": len(selected),
        "selected_ids": selected_ids,
        "returned_ids": returned_ids,
        "extracted_count": int(summary.get("fetched_listings") or 0),
        "visible_count": int(summary.get("visible_listings") or 0),
        "hidden_count": int(summary.get("hidden_by_filter") or 0),
        "malformed_count": len(malformed),
        "malformed": malformed,
        "title_empty_count": sum(item["reason"] == "title_empty" for item in malformed),
        "anzeige_link_missing_count": sum(item["reason"] == "anzeige_link_missing" for item in malformed),
        "reported_total": summary.get("reported_total"),
        "next_link": _next_link_evidence(source),
        "actual_source_url": pagination.get("actual_source_url"),
        "requested_cursor_url": pagination.get("requested_cursor_url"),
        "stop_reason": pagination.get("stop_reason"),
        "raw_html_persisted": False,
        "article_excerpt_limit": 800,
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
    result["coverage_diagnostics"] = _card_evidence(source, result)
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "coverage_evidence": True,
        "title_evidence": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
