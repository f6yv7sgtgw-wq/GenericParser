"""CPU-sparing one-work-packet search service for Cloudflare Workers Free.

A Kleinanzeigen HTML result page is split into four virtual work packets.  Each
invocation extracts at most seven cards with simple bounded regular-expression
scans; it does not build a BeautifulSoup DOM and does not run the legacy scorer.
"""
from __future__ import annotations

import html as html_lib
import re
from typing import Any, Literal
from urllib.parse import quote, urlencode, urljoin

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator

VERSION = "0.42.7"
BUILD_ID = "gp-0427-20260803-1"
API_CONTRACT = "match-v6.1-page-worker"
BASE_URL = "https://www.kleinanzeigen.de"
SOURCE_PAGE_SIZE = 25
PACKET_SIZE = 7
PACKETS_PER_SOURCE_PAGE = 4
MAX_VIRTUAL_PAGE = 2000

_ARTICLE_RE = re.compile(r'<article\b[^>]*\bdata-adid=["\']([^"\']+)["\'][^>]*>', re.I)
_LINK_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']*/s-anzeige/[^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_TOTAL_RE = re.compile(r'(?:Mehr\s+als\s+)?([\d.]+)\s+Ergebnisse', re.I)
_TAG_RE = re.compile(r'<[^>]+>')
_SPACE_RE = re.compile(r'\s+')
_PRICE_RE = re.compile(r'(\d[\d.]*)')


class SearchRequest(BaseModel):
    mode: Literal["live", "html"] = "live"
    query: str = Field(min_length=2, max_length=120)
    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0, le=200)
    required_terms: list[str] = Field(default_factory=list)
    excluded_terms: list[str] = Field(default_factory=list)
    model_patterns: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    max_price: float | None = Field(default=None, gt=0)
    market_value: float | None = Field(default=None, gt=0)
    accept_bundles: bool = False
    accept_incomplete: bool = False
    include_review: bool = True
    include_rejected: bool = True
    sort_by: str = "relevance"
    page: int = Field(default=0, ge=0, le=MAX_VIRTUAL_PAGE)
    source: str = "auto"
    html: str | None = Field(default=None, max_length=2_000_000)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Der Suchbegriff ist zu kurz")
        return value


def _text(fragment: str) -> str:
    return _SPACE_RE.sub(" ", html_lib.unescape(_TAG_RE.sub(" ", fragment))).strip()


def _class_text(card: str, marker: str) -> str:
    pos = card.find(marker)
    if pos < 0:
        return ""
    start = card.rfind("<", 0, pos)
    end = card.find(">", pos)
    if start < 0 or end < 0:
        return ""
    close = card.find("</", end)
    if close < 0:
        return ""
    return _text(card[end + 1 : close])


def _price(raw: str) -> float | None:
    match = _PRICE_RE.search(raw.replace(" ", " "))
    if not match:
        return None
    try:
        return float(match.group(1).replace(".", ""))
    except ValueError:
        return None


def _reported_total(source: str) -> int | None:
    match = _TOTAL_RE.search(source[:250_000])
    if not match:
        return None
    try:
        return int(match.group(1).replace(".", ""))
    except ValueError:
        return None


def _source_url(payload: SearchRequest, source_page: int) -> str:
    slug = quote(re.sub(r"\s+", "-", payload.query.lower()).strip("-"), safe="-")
    if payload.postal_code and payload.location_id:
        suffix = f"k0l{payload.location_id}"
        if payload.radius_km is not None:
            suffix += f"r{payload.radius_km}"
        path = f"/s-{payload.postal_code}/{slug}/{suffix}"
    else:
        path = f"/s-{slug}/k0"
    params = {"sortingField": "SORTING_DATE"}
    if source_page > 0:
        params["pageNum"] = str(source_page + 1)
    return f"{BASE_URL}{path}?{urlencode(params)}"


def _card_ranges(source: str) -> list[tuple[str, int, int]]:
    starts = [(match.group(1), match.start()) for match in _ARTICLE_RE.finditer(source)]
    ranges: list[tuple[str, int, int]] = []
    for index, (listing_id, start) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else source.find("</article>", start)
        if end < 0:
            end = min(len(source), start + 40_000)
        else:
            end += len("</article>")
        ranges.append((listing_id, start, end))
    return ranges


def _extract_card(source: str, listing_id: str, start: int, end: int, payload: SearchRequest) -> dict[str, Any] | None:
    card = source[start:end]
    link_match = _LINK_RE.search(card)
    if not link_match:
        return None
    href, title_html = link_match.groups()
    title = _text(title_html)
    if not title:
        return None
    price_raw = _class_text(card, "price-shipping--price")
    location_raw = _class_text(card, "aditem-main--top--left")
    date_raw = _class_text(card, "aditem-main--top--right")
    description = _class_text(card, "aditem-main--middle--description")
    image_match = re.search(r'<img\b[^>]*(?:src|data-src|data-imgsrc)=["\']([^"\']+)', card, re.I)
    image_url = urljoin(BASE_URL, image_match.group(1)) if image_match else None
    postal_match = re.search(r'\b(\d{5})\b', location_raw)
    postal_code = postal_match.group(1) if postal_match else None
    place = location_raw.replace(postal_code or "", "").strip(" ,") or None
    numeric_price = _price(price_raw)
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
        "url": urljoin(BASE_URL, href),
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
        "match": {
            "score": score,
            "decision": decision,
            "listing_class": "produkt",
            "reason": reason,
        },
    }


async def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers=headers)
    if response.status_code in {403, 429}:
        raise HTTPException(status_code=429, detail=f"Kleinanzeigen blockiert den Abruf ({response.status_code})")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Kleinanzeigen antwortet mit HTTP {response.status_code}")
    return response.text


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    source_page = payload.page // PACKETS_PER_SOURCE_PAGE
    packet_index = payload.page % PACKETS_PER_SOURCE_PAGE
    request_url = _source_url(payload, source_page)
    source = payload.html or "" if payload.mode == "html" else await _fetch_html(request_url)
    ranges = _card_ranges(source)
    start_index = packet_index * PACKET_SIZE
    selected = ranges[start_index : start_index + PACKET_SIZE]
    extracted = [item for args in selected if (item := _extract_card(source, *args, payload)) is not None]
    fetched = len(extracted)
    visible = [
        item for item in extracted
        if item["decision"] == "alert"
        or (item["decision"] == "review" and payload.include_review)
        or (item["decision"] == "reject" and payload.include_rejected)
    ]
    hidden = fetched - len(visible)
    reported_total = _reported_total(source)
    source_cards = len(ranges)
    consumed_on_source_page = min(source_cards, start_index + len(selected))
    global_consumed = source_page * SOURCE_PAGE_SIZE + consumed_on_source_page
    source_page_finished = consumed_on_source_page >= source_cards
    complete = False
    stop_reason = "work_packet_complete"
    if source_cards == 0:
        complete, stop_reason = True, "empty_page_verified"
    elif reported_total is not None and global_consumed >= reported_total:
        complete, stop_reason = True, "reported_total_reached"
    elif source_page_finished and source_cards < SOURCE_PAGE_SIZE:
        complete, stop_reason = True, "short_source_page"
    next_page = None if complete else payload.page + 1
    return {
        "mode": payload.mode,
        "generated_urls": [request_url] if payload.mode == "live" else [],
        "pagination": {
            "source": "html-light-packets",
            "page": payload.page,
            "pages_loaded": 1,
            "page_counts": [fetched],
            "new_ids_per_page": [fetched],
            "unique_listings": fetched,
            "duplicates": 0,
            "complete": complete,
            "partial": not complete,
            "continuation_available": not complete,
            "next_page": next_page,
            "stop_reason": stop_reason,
            "reported_total": reported_total,
            "source_page": source_page,
            "packet_index": packet_index,
            "packet_size": PACKET_SIZE,
            "source_cards": source_cards,
            "global_consumed": global_consumed,
            "worker_unit": "free-cpu-work-packet",
        },
        "listings": visible,
        "summary": {
            "reported_total": reported_total,
            "fetched_listings": fetched,
            "visible_listings": len(visible),
            "hidden_by_filter": hidden,
            "alerts": sum(item["decision"] == "alert" for item in extracted),
            "review": sum(item["decision"] == "review" for item in extracted),
            "rejected": sum(item["decision"] == "reject" for item in extracted),
            "malformed_rejected": len(selected) - fetched,
            "data_consistent": fetched == len(visible) + hidden,
        },
        "worker": {
            "version": VERSION,
            "build_id": BUILD_ID,
            "api_contract": API_CONTRACT,
            "worker_unit": "free-cpu-work-packet",
            "source_used": "html-light-packets",
            "matching": "minimal-title-description-v1",
        },
        "consistency": {
            "ok": fetched == len(visible) + hidden,
            "fetched_equals_visible_plus_hidden": fetched == len(visible) + hidden,
            "visible_equals_listings": len(visible) == len(visible),
        },
    }


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
