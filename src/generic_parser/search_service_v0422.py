"""App-free one-page Kleinanzeigen search service for GenericParser 0.42.2."""
from __future__ import annotations

import re
from typing import Any

import httpx
from fastapi import HTTPException, Request
from pydantic import Field

from . import cloudflare_app as core
from . import cloudflare_v03 as legacy
from . import cloudflare_v037 as scope
from . import cloudflare_v038 as dynamic
from .matching import score_listing, sort_results
from .models import Listing, MatchDecision
from .sources.kleinanzeigen import KleinanzeigenBlockedError, KleinanzeigenLayoutError, KleinanzeigenUrlBuilder

VERSION = "0.42.2"
BUILD_ID = "gp-0422-20260802-1"
API_CONTRACT = "match-v6.1-page-worker"
MOBILE_PAGE_SIZE = 41
MAX_PAGE = 500


class SearchRequest(legacy.SearchRequest):
    page: int = Field(default=0, ge=0, le=MAX_PAGE)
    source: str = Field(default="auto", pattern="^(auto|mobile-api|html-fallback)$")


def _valid_listing(item: Listing) -> bool:
    title = (item.title or "").strip()
    url = (item.url or "").strip()
    return bool(item.id and title and url and "<" not in title and ">" not in title and "<" not in url)


def _valid_count(parsed: Any) -> int:
    return sum(1 for item in parsed.listings if _valid_listing(item))


def _html_reported_total(text: str) -> int | None:
    for pattern in (r"Mehr\s+als\s+([\d.]+)\s+Ergebnisse", r"([\d.]+)\s+Ergebnisse", r'"total(?:ResultCount|Results|Count)"\s*:\s*(\d+)'):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace(".", ""))
            except ValueError:
                pass
    return None


async def _mobile_page(payload: SearchRequest) -> tuple[Any, int | None, dict[str, Any]]:
    headers = {"Authorization": f"Basic {core.MOBILE_API_BASIC_AUTH}", "User-Agent": "okhttp/4.10.0", "Accept": "application/json", "X-EBAYK-APP": "genericparser-cloudflare"}
    request_url = core._mobile_url(payload, page=payload.page, size=MOBILE_PAGE_SIZE)
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        response = await client.get(request_url, headers=headers)
    diagnostics = {"request_url": request_url, "http_status": response.status_code, "response_bytes": len(response.content)}
    if response.status_code in {401, 403, 429}:
        raise KleinanzeigenBlockedError(f"Kleinanzeigen-App-API verweigert den Zugriff ({response.status_code})")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Kleinanzeigen-App-API antwortet mit HTTP {response.status_code}")
    data = response.json()
    parsed = core._parse_mobile(data, payload.query, page=payload.page)
    diagnostics.update(raw_cards=parsed.diagnostics.cards_found, parsed_listings=len(parsed.listings), valid_listings=_valid_count(parsed))
    return parsed, scope._extract_reported_total(data), diagnostics


async def _html_page(payload: SearchRequest, url: str) -> tuple[Any, int | None]:
    page_url = dynamic._html_page_url(url, payload.page)
    page = await core.fetch_search_page(page_url)
    parsed = core.CloudflarePageParser().parse(page, source_query=payload.query)
    return parsed, _html_reported_total(page.text)


def _page_contract(*, source: str, page: int, count: int, complete: bool, stop_reason: str, reported_total: int | None, fallback_reason: str | None, mobile_diagnostics: dict[str, Any] | None) -> dict[str, Any]:
    return {"source": source, "page": page, "pages_loaded": 1, "page_counts": [count], "new_ids_per_page": [count], "unique_listings": count, "duplicates": 0, "complete": complete, "partial": not complete, "continuation_available": not complete, "next_page": None if complete else page + 1, "stop_reason": stop_reason, "reported_total": reported_total, "fallback_reason": fallback_reason, "mobile_diagnostics": mobile_diagnostics, "worker_unit": "one-page-service"}


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    legacy._token(request)
    profile = legacy._profile(payload)
    url = KleinanzeigenUrlBuilder().keyword_url(profile, payload.query)
    reported_total = None
    fallback_reason = None
    mobile_diagnostics = None
    source_used = payload.source

    try:
        if payload.mode == "html":
            page = core.FetchedPage("inline://html", "inline://html", 200, payload.html or "")
            parsed = core.CloudflarePageParser().parse(page, source_query=payload.query)
            reported_total = _html_reported_total(payload.html or "")
            source_used = "html"
        elif payload.source == "html-fallback":
            parsed, reported_total = await _html_page(payload, url)
            source_used = "html-fallback"
        else:
            try:
                parsed, reported_total, mobile_diagnostics = await _mobile_page(payload)
                source_used = "mobile-api"
                if payload.page == 0 and _valid_count(parsed) == 0:
                    fallback_reason = "mobile_first_page_empty"
                    html_parsed, html_total = await _html_page(payload, url)
                    if _valid_count(html_parsed) > 0:
                        parsed, reported_total, source_used = html_parsed, html_total if html_total is not None else reported_total, "html-fallback"
                    else:
                        fallback_reason = "mobile_and_html_first_page_empty"
            except (KleinanzeigenBlockedError, HTTPException, httpx.RequestError, KleinanzeigenLayoutError, ValueError) as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"
                parsed, reported_total = await _html_page(payload, url)
                source_used = "html-fallback"
    except KleinanzeigenBlockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except KleinanzeigenLayoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Kleinanzeigen ist nicht erreichbar") from exc

    clean = tuple(item for item in parsed.listings if _valid_listing(item))
    malformed = len(parsed.listings) - len(clean)
    scored = [score_listing(item, profile) for item in clean]
    alerts = [item for item in scored if item.decision is MatchDecision.ALERT]
    review = [item for item in scored if item.decision is MatchDecision.REVIEW]
    rejected = [item for item in scored if item.decision is MatchDecision.REJECT]
    visible = sort_results(alerts + (review if payload.include_review else []) + (rejected if payload.include_rejected else []), payload.sort_by)
    count = len(clean)
    if payload.mode == "html": complete, stop_reason = True, "html_mode"
    elif count == 0: complete, stop_reason = True, "empty_page_verified"
    elif source_used == "mobile-api" and count < MOBILE_PAGE_SIZE: complete, stop_reason = True, "short_page"
    else: complete, stop_reason = False, "page_complete"

    data_consistent = count == len(scored) and len(visible) <= len(scored)
    return {
        "mode": payload.mode,
        "generated_urls": [url] if payload.mode == "live" else [],
        "pagination": _page_contract(source=source_used, page=payload.page, count=count, complete=complete, stop_reason=stop_reason, reported_total=reported_total, fallback_reason=fallback_reason, mobile_diagnostics=mobile_diagnostics),
        "listings": [legacy._listing(item) for item in visible],
        "summary": {"reported_total": reported_total, "fetched_listings": count, "visible_listings": len(visible), "hidden_by_filter": len(scored)-len(visible), "alerts": len(alerts), "review": len(review), "rejected": len(rejected), "malformed_rejected": malformed, "data_consistent": data_consistent, "empty_mobile_fallback_used": fallback_reason == "mobile_first_page_empty" and source_used == "html-fallback"},
        "worker": {"version": VERSION, "build_id": BUILD_ID, "api_contract": API_CONTRACT, "worker_unit": "app-free-one-page-service", "source_used": source_used, "matching": "score-v1-non-destructive-default"},
    }
