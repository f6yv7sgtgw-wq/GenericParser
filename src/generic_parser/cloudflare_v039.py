from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import Field

from . import cloudflare_app as core
from . import cloudflare_v03 as legacy
from . import cloudflare_v037 as scope
from . import cloudflare_v038 as dynamic
from .matching import score_listing, sort_results
from .models import Listing, MatchDecision
from .sources.kleinanzeigen import KleinanzeigenBlockedError, KleinanzeigenLayoutError, KleinanzeigenUrlBuilder

VERSION = "0.39.0"
MOBILE_PAGE_SIZE = 41
MAX_PAGE = 500


class SearchRequest(legacy.SearchRequest):
    page: int = Field(default=0, ge=0, le=MAX_PAGE)
    source: str = Field(default="auto", pattern="^(auto|mobile-api|html-fallback)$")


def _valid_listing(item: Listing) -> bool:
    """Reject malformed parser output instead of exposing raw HTML as a listing."""
    title = (item.title or "").strip()
    url = (item.url or "").strip()
    return bool(item.id and title and url and "<" not in title and ">" not in title and "<" not in url)


def _page_contract(*, source: str, page: int, count: int, complete: bool, stop_reason: str,
                   reported_total: int | None, fallback_reason: str | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "page": page,
        "pages_loaded": 1,
        "page_counts": [count],
        "new_ids_per_page": [count],
        "unique_listings": count,
        "duplicates": 0,
        "complete": complete,
        "partial": not complete,
        "continuation_available": not complete,
        "next_page": None if complete else page + 1,
        "stop_reason": stop_reason,
        "reported_total": reported_total,
        "fallback_reason": fallback_reason,
        "worker_unit": "one-page",
    }


async def _mobile_page(payload: SearchRequest) -> tuple[Any, int | None]:
    headers = {
        "Authorization": f"Basic {core.MOBILE_API_BASIC_AUTH}",
        "User-Agent": "okhttp/4.10.0",
        "Accept": "application/json",
        "X-EBAYK-APP": "genericparser-cloudflare",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        response = await client.get(core._mobile_url(payload, page=payload.page, size=MOBILE_PAGE_SIZE), headers=headers)
    if response.status_code in {401, 403, 429}:
        raise KleinanzeigenBlockedError(f"Kleinanzeigen-App-API verweigert den Zugriff ({response.status_code})")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Kleinanzeigen-App-API antwortet mit HTTP {response.status_code}")
    data = response.json()
    parsed = core._parse_mobile(data, payload.query, page=payload.page)
    return parsed, scope._extract_reported_total(data)


async def _html_page(payload: SearchRequest, url: str) -> Any:
    page_url = dynamic._html_page_url(url, payload.page)
    page = await core.fetch_search_page(page_url)
    return core.CloudflarePageParser().parse(page, source_query=payload.query)


app = FastAPI(title="GenericParser Page Worker", version=VERSION, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "version": VERSION, "runtime": "cloudflare-worker", "worker_unit": "one-page"}


@app.post("/api/location-id")
async def location_id(payload: legacy.LocationRequest, request: Request) -> dict[str, int]:
    return await legacy.location_id(payload, request)


@app.post("/api/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    legacy._token(request)
    profile = legacy._profile(payload)
    url = KleinanzeigenUrlBuilder().keyword_url(profile, payload.query)
    reported_total: int | None = None
    fallback_reason: str | None = None
    source_used = payload.source

    try:
        if payload.mode == "html":
            page = core.FetchedPage("inline://html", "inline://html", 200, payload.html or "")
            parsed = core.CloudflarePageParser().parse(page, source_query=payload.query)
            source_used = "html"
        elif payload.source == "html-fallback":
            parsed = await _html_page(payload, url)
            source_used = "html-fallback"
        else:
            try:
                parsed, reported_total = await _mobile_page(payload)
                source_used = "mobile-api"
            except (KleinanzeigenBlockedError, HTTPException, httpx.RequestError, KleinanzeigenLayoutError, ValueError) as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"
                parsed = await _html_page(payload, url)
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
    visible = alerts + (review if payload.include_review else []) + (rejected if payload.include_rejected else [])
    visible = sort_results(visible, payload.sort_by)

    count = len(clean)
    if payload.mode == "html":
        complete, stop_reason = True, "html_mode"
    elif count == 0:
        complete, stop_reason = True, "empty_page"
    elif source_used == "mobile-api" and count < MOBILE_PAGE_SIZE:
        complete, stop_reason = True, "short_page"
    else:
        complete, stop_reason = False, "page_complete"

    pagination = _page_contract(
        source=source_used, page=payload.page, count=count, complete=complete,
        stop_reason=stop_reason, reported_total=reported_total, fallback_reason=fallback_reason,
    )
    return {
        "mode": payload.mode,
        "generated_urls": [url] if payload.mode == "live" else [],
        "pagination": pagination,
        "listings": [legacy._listing(item) for item in visible],
        "summary": {
            "reported_total": reported_total,
            "fetched_listings": count,
            "visible_listings": len(visible),
            "hidden_by_filter": len(scored) - len(visible),
            "alerts": len(alerts), "review": len(review), "rejected": len(rejected),
            "malformed_rejected": malformed,
            "data_consistent": count == len(scored),
        },
        "worker": {
            "version": VERSION,
            "worker_unit": "one-page",
            "source_used": source_used,
            "api_contract": "match-v6-page-worker",
            "matching": "score-v1-non-destructive-default",
        },
    }
