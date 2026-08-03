"""GenericParser 0.43.6 robust title extraction.

Keeps the proven 0.43.3 search state machine, real next-link pagination and the
0.43.5 bounded diagnostics. Only card title extraction is extended.
"""
from __future__ import annotations

import html as html_lib
import re
from typing import Any
from urllib.parse import urljoin
from fastapi import Request

from . import search_service_v0430 as flow
from . import search_service_v0435 as evidence
from .build_identity_v0436 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = flow.SearchRequest

_H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.I | re.S)
_ANCHOR_RE = re.compile(r"<a\b([^>]*)href=[\"']([^\"']*/s-anzeige/[^\"']+)[\"']([^>]*)>(.*?)</a>", re.I | re.S)
_ARTICLE_OPEN_RE = re.compile(r"<article\b([^>]*)>", re.I | re.S)
_IMG_ALT_RE = re.compile(r"<img\b[^>]*\balt=[\"']([^\"']+)[\"']", re.I | re.S)
_IMG_SRC_RE = re.compile(r"<img\b[^>]*(?:src|data-src|data-imgsrc)=[\"']([^\"']+)", re.I)
_ATTR_TEMPLATE = r"\b%s\s*=\s*[\"']([^\"']*)[\"']"
_LOCATION_SUFFIX_RE = re.compile(r"\s+(?:\d{5}\s+)?[^|]{1,80}\s+Vorschau\s*$", re.I)
_PREVIEW_SUFFIX_RE = re.compile(r"\s+Vorschau\s*$", re.I)


def _attr(fragment: str, name: str) -> str | None:
    match = re.search(_ATTR_TEMPLATE % re.escape(name), fragment, re.I | re.S)
    return html_lib.unescape(match.group(1)).strip() if match else None


def _first_nonempty(values: list[tuple[str, str | None]]) -> tuple[str, str] | tuple[None, None]:
    for strategy, value in values:
        if value and value.strip():
            return value.strip(), strategy
    return None, None


def _clean_alt_title(value: str | None) -> str | None:
    if not value:
        return None
    text = html_lib.unescape(value).strip()
    text = _PREVIEW_SUFFIX_RE.sub("", text)
    text = _LOCATION_SUFFIX_RE.sub("", text)
    return text.strip() or None


def _extract_card_robust(source: str, listing_id: str, start: int, end: int, payload: SearchRequest) -> dict[str, Any] | None:
    card = source[start:end]
    article_match = _ARTICLE_OPEN_RE.search(card)
    article_attrs = article_match.group(1) if article_match else ""
    data_href = _attr(article_attrs, "data-href")

    anchors = list(_ANCHOR_RE.finditer(card))
    first_href = anchors[0].group(2) if anchors else data_href
    if not first_href:
        return None

    h2_match = _H2_RE.search(card)
    h2_title = flow.base._text(h2_match.group(1)) if h2_match else None

    nonempty_link_text = None
    aria_title = None
    attr_title = None
    for match in anchors:
        attrs = f"{match.group(1)} {match.group(3)}"
        body_text = flow.base._text(match.group(4))
        if not nonempty_link_text and body_text:
            nonempty_link_text = body_text
        if not aria_title:
            aria_title = _attr(attrs, "aria-label")
        if not attr_title:
            attr_title = _attr(attrs, "title")

    img_match = _IMG_ALT_RE.search(card)
    image_alt = _clean_alt_title(img_match.group(1) if img_match else None)
    title, title_strategy = _first_nonempty([
        ("h2", h2_title),
        ("anzeige_link_text", nonempty_link_text),
        ("aria_label", aria_title),
        ("title_attribute", attr_title),
        ("image_alt", image_alt),
    ])
    if not title:
        return None

    price_raw = flow.base._class_text(card, "price-shipping--price")
    location_raw = flow.base._class_text(card, "aditem-main--top--left")
    date_raw = flow.base._class_text(card, "aditem-main--top--right")
    description = flow.base._class_text(card, "aditem-main--middle--description")
    image_match = _IMG_SRC_RE.search(card)
    image_url = urljoin(flow.base.BASE_URL, image_match.group(1)) if image_match else None
    postal_match = re.search(r"\b(\d{5})\b", location_raw)
    postal_code = postal_match.group(1) if postal_match else None
    place = location_raw.replace(postal_code or "", "").strip(" ,") or None
    numeric_price = flow.base._price(price_raw)
    haystack = f"{title} {description}".casefold()
    missing = [term for term in payload.required_terms if term.casefold() not in haystack]
    excluded = [term for term in payload.excluded_terms if term.casefold() in haystack]
    if missing:
        decision, score, reason = "reject", 0, "Pflichtbegriffe fehlen: " + ", ".join(missing)
    elif excluded:
        decision, score, reason = "reject", 0, "Ausschlussbegriff gefunden: " + ", ".join(excluded)
    elif payload.max_price is not None and numeric_price is not None and numeric_price > payload.max_price:
        decision, score, reason = "reject", 10, "Maximalpreis überschritten"
    elif payload.required_terms:
        decision, score, reason = "alert", 100, "Alle Pflichtbegriffe erfüllt"
    else:
        decision, score, reason = "review", 70, "Leichtgewichtiger Free-Tarif-Treffer"

    return {
        "id": listing_id,
        "title": title,
        "url": urljoin(flow.base.BASE_URL, data_href or first_href),
        "price": numeric_price,
        "price_raw": price_raw or None,
        "postal_code": postal_code,
        "place": place,
        "posted_at": date_raw or None,
        "description": description or None,
        "source_query": payload.query,
        "tags": [],
        "image_url": image_url,
        "score": score,
        "decision": decision,
        "title_strategy": title_strategy,
        "match": {"score": score, "decision": decision, "listing_class": "produkt", "reason": reason},
    }


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    captured: dict[str, str] = {}
    original_fetch = flow.base._fetch_html
    original_extract = flow.base._extract_card

    async def capture_fetch(url: str) -> str:
        source = await original_fetch(url)
        captured["url"] = url
        captured["html"] = source
        return source

    flow.base._fetch_html = capture_fetch
    flow.base._extract_card = _extract_card_robust
    try:
        result = await flow.search_page(payload, request)
    finally:
        flow.base._fetch_html = original_fetch
        flow.base._extract_card = original_extract

    source = captured.get("html", payload.html or "")
    diagnostics = evidence._card_evidence(source, result)
    strategies: dict[str, int] = {}
    for item in result.get("listings") or []:
        strategy = str(item.get("title_strategy") or "unknown")
        strategies[strategy] = strategies.get(strategy, 0) + 1
    diagnostics.update({
        "schema": "robust-title-v1",
        "title_strategy_counts": strategies,
        "title_fallback_active": True,
        "title_order": ["h2", "anzeige_link_text", "aria_label", "title_attribute", "image_alt"],
    })
    result["coverage_diagnostics"] = diagnostics
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "robust_title_fallback": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
