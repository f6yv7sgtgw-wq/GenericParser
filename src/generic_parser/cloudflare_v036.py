from __future__ import annotations

from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import Field

from . import cloudflare_app as core
from . import cloudflare_v03 as legacy
from .matching import score_listing, sort_results
from .models import Listing, MatchDecision
from .sources.kleinanzeigen import KleinanzeigenBlockedError, KleinanzeigenLayoutError, KleinanzeigenUrlBuilder

VERSION = "0.36.0"
MOBILE_PAGE_BUDGET = 4
HTML_PAGE_BUDGET = 2
MOBILE_PAGE_SIZE = 41
MAX_CURSOR_PAGE = 500


class SearchRequest(legacy.SearchRequest):
    cursor_page: int = Field(default=0, ge=0, le=MAX_CURSOR_PAGE)
    cursor_source: Literal["auto", "mobile-api", "html-fallback"] = "auto"


def _chunk_pagination(
    *,
    source: str,
    start_page: int,
    pages_loaded: int,
    page_counts: list[int],
    new_counts: list[int],
    duplicates: int,
    stop_reason: str,
    complete: bool,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    next_page = None if complete else start_page + pages_loaded
    return {
        "source": source,
        "start_page": start_page,
        "next_page": next_page,
        "pages_loaded": pages_loaded,
        "page_counts": page_counts,
        "new_ids_per_page": new_counts,
        "duplicates": duplicates,
        "unique_listings": sum(new_counts),
        "stop_reason": stop_reason,
        "complete": complete,
        "partial": not complete,
        "continuation_available": next_page is not None,
        "request_page_budget": MOBILE_PAGE_BUDGET if source == "mobile-api" else HTML_PAGE_BUDGET,
        "fallback_reason": fallback_reason,
    }


async def _mobile_chunk(payload: SearchRequest) -> tuple[Any, dict[str, Any]]:
    headers = {
        "Authorization": f"Basic {core.MOBILE_API_BASIC_AUTH}",
        "User-Agent": "okhttp/4.10.0",
        "Accept": "application/json",
        "X-EBAYK-APP": "genericparser-cloudflare",
    }
    listings: list[Listing] = []
    seen: set[str] = set()
    signatures: set[tuple[str, ...]] = set()
    errors = []
    cards = duplicates = pages_loaded = 0
    page_counts: list[int] = []
    new_counts: list[int] = []
    stop_reason = "chunk_budget_reached"
    complete = False
    remaining = legacy._effective_limit(payload)

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
        for offset in range(MOBILE_PAGE_BUDGET):
            page_number = payload.cursor_page + offset
            page_size = min(MOBILE_PAGE_SIZE, remaining) if remaining else MOBILE_PAGE_SIZE
            response = await client.get(core._mobile_url(payload, page=page_number, size=page_size), headers=headers)
            if response.status_code in {401, 403, 429}:
                raise KleinanzeigenBlockedError(f"Kleinanzeigen-App-API verweigert den Zugriff ({response.status_code})")
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Kleinanzeigen-App-API antwortet mit HTTP {response.status_code}")
            parsed = core._parse_mobile(response.json(), payload.query, page=page_number)
            pages_loaded += 1
            count = len(parsed.listings)
            page_counts.append(count)
            cards += parsed.diagnostics.cards_found
            errors.extend(parsed.diagnostics.errors)
            if count == 0:
                new_counts.append(0)
                stop_reason, complete = "empty_page", True
                break
            signature = tuple(item.id for item in parsed.listings)
            if signature in signatures:
                duplicates += count
                new_counts.append(0)
                stop_reason, complete = "repeated_page", True
                break
            signatures.add(signature)
            added = 0
            for item in parsed.listings:
                if item.id in seen:
                    duplicates += 1
                    continue
                seen.add(item.id)
                listings.append(item)
                added += 1
                if remaining is not None and len(listings) >= remaining:
                    break
            new_counts.append(added)
            if remaining is not None and len(listings) >= remaining:
                stop_reason, complete = "user_limit_reached", True
                break
            if added == 0:
                stop_reason, complete = "no_new_ids", True
                break
            if count < page_size:
                stop_reason, complete = "short_page", True
                break

    url = f"mobile-api://pages/{payload.cursor_page}-{payload.cursor_page + pages_loaded - 1}"
    parsed_page = core.ParsedPage(
        tuple(listings),
        core.PageDiagnostics(core.PageState.RESULTS if listings else core.PageState.NO_RESULTS, url, url, cards, len(listings), duplicates, tuple(errors)),
    )
    return parsed_page, _chunk_pagination(
        source="mobile-api", start_page=payload.cursor_page, pages_loaded=pages_loaded,
        page_counts=page_counts, new_counts=new_counts, duplicates=duplicates,
        stop_reason=stop_reason, complete=complete,
    )


async def _html_chunk(payload: SearchRequest, base_url: str, *, fallback_reason: str | None = None) -> tuple[Any, dict[str, Any]]:
    parser = core.CloudflarePageParser()
    listings: list[Listing] = []
    seen: set[str] = set()
    signatures: set[tuple[str, ...]] = set()
    errors = []
    cards = duplicates = pages_loaded = 0
    page_counts: list[int] = []
    new_counts: list[int] = []
    stop_reason = "chunk_budget_reached"
    complete = False
    remaining = legacy._effective_limit(payload)

    for offset in range(HTML_PAGE_BUDGET):
        page_number = payload.cursor_page + offset
        page = await core.fetch_search_page(legacy._html_page_url(base_url, page_number))
        parsed = parser.parse(page, source_query=payload.query)
        pages_loaded += 1
        count = len(parsed.listings)
        page_counts.append(count)
        cards += parsed.diagnostics.cards_found
        errors.extend(parsed.diagnostics.errors)
        if count == 0:
            new_counts.append(0)
            stop_reason, complete = "empty_page", True
            break
        signature = tuple(item.id for item in parsed.listings)
        if signature in signatures:
            duplicates += count
            new_counts.append(0)
            stop_reason, complete = "repeated_page", True
            break
        signatures.add(signature)
        added = 0
        for item in parsed.listings:
            if item.id in seen:
                duplicates += 1
                continue
            seen.add(item.id)
            listings.append(item)
            added += 1
            if remaining is not None and len(listings) >= remaining:
                break
        new_counts.append(added)
        if remaining is not None and len(listings) >= remaining:
            stop_reason, complete = "user_limit_reached", True
            break
        if added == 0:
            stop_reason, complete = "no_new_ids", True
            break

    requested = legacy._html_page_url(base_url, payload.cursor_page)
    parsed_page = core.ParsedPage(
        tuple(listings),
        core.PageDiagnostics(core.PageState.RESULTS if listings else core.PageState.NO_RESULTS, requested, requested, cards, len(listings), duplicates, tuple(errors)),
    )
    return parsed_page, _chunk_pagination(
        source="html-fallback", start_page=payload.cursor_page, pages_loaded=pages_loaded,
        page_counts=page_counts, new_counts=new_counts, duplicates=duplicates,
        stop_reason=stop_reason, complete=complete, fallback_reason=fallback_reason,
    )


app = FastAPI(title="GenericParser Cursor Worker", version=VERSION, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "version": VERSION, "runtime": "cloudflare-worker", "pagination": "cursor-v1"}


@app.post("/api/location-id")
async def location_id(payload: legacy.LocationRequest, request: Request) -> dict[str, int]:
    return await legacy.location_id(payload, request)


@app.post("/api/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    legacy._token(request)
    profile = legacy._profile(payload)
    url = KleinanzeigenUrlBuilder().keyword_url(profile, payload.query)

    try:
        if payload.mode == "html":
            page = core.FetchedPage("inline://html", "inline://html", 200, payload.html or "")
            parsed = core.CloudflarePageParser().parse(page, source_query=payload.query)
            pagination = _chunk_pagination(source="html", start_page=0, pages_loaded=1, page_counts=[len(parsed.listings)], new_counts=[len(parsed.listings)], duplicates=parsed.diagnostics.duplicates_skipped, stop_reason="html_mode", complete=True)
        elif payload.cursor_source == "html-fallback":
            parsed, pagination = await _html_chunk(payload, url)
        else:
            try:
                parsed, pagination = await _mobile_chunk(payload)
                if payload.cursor_page == 0 and not parsed.listings:
                    payload.cursor_page = 0
                    parsed, pagination = await _html_chunk(payload, url, fallback_reason="mobile_empty")
            except (KleinanzeigenBlockedError, HTTPException, httpx.RequestError, KleinanzeigenLayoutError) as exc:
                if payload.cursor_page > 0 and payload.cursor_source == "mobile-api":
                    raise
                payload.cursor_page = 0
                parsed, pagination = await _html_chunk(payload, url, fallback_reason=f"{type(exc).__name__}: {exc}")
    except KleinanzeigenBlockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except KleinanzeigenLayoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Kleinanzeigen ist nicht erreichbar") from exc

    raw = parsed.listings
    scored = [score_listing(item, profile) for item in raw]
    alerts = [item for item in scored if item.decision is MatchDecision.ALERT]
    review = [item for item in scored if item.decision is MatchDecision.REVIEW]
    rejected = [item for item in scored if item.decision is MatchDecision.REJECT]
    visible = alerts + (review if payload.include_review else []) + (rejected if payload.include_rejected else [])
    visible = sort_results(visible, payload.sort_by)

    return {
        "mode": payload.mode,
        "generated_urls": [url] if payload.mode == "live" else [],
        "diagnostics": [legacy._diagnostic(parsed.diagnostics)],
        "pagination": pagination,
        "listings": [legacy._listing(item) for item in visible],
        "summary": {
            "fetched_listings": len(raw), "scored_listings": len(scored), "visible_listings": len(visible),
            "hidden_by_filter": len(scored) - len(visible), "alerts": len(alerts), "review": len(review),
            "rejected": len(rejected), "duplicates": pagination["duplicates"], "pages_loaded": pagination["pages_loaded"],
            "data_consistent": len(raw) == pagination["unique_listings"],
        },
        "worker": {
            "version": VERSION, "pagination": "cursor-v1", "source_used": pagination["source"],
            "matching": "score-v1-non-destructive-default", "api_contract": "match-v3-cursor",
        },
    }
