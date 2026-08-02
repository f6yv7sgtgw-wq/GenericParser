from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, Request

from . import cloudflare_v036 as cursor
from . import cloudflare_v037 as scope

VERSION = "0.38.0"
FULL_SEARCH_THRESHOLD = 100
CONTINUATION_SEARCH_THRESHOLD = 500
BROAD_SEARCH_THRESHOLD = 500

SearchRequest = cursor.SearchRequest


def _html_page_url(base_url: str, page_number: int) -> str:
    """Map internal zero-based cursor pages to Kleinanzeigen' one-based pageNum values."""
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if page_number <= 0:
        query.pop("pageNum", None)
    else:
        query["pageNum"] = str(page_number + 1)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _search_scope(reported_total: int | None, targeted: bool) -> str:
    if targeted:
        return "targeted"
    if reported_total is None:
        return "continuation"
    if reported_total <= FULL_SEARCH_THRESHOLD:
        return "complete"
    if reported_total <= CONTINUATION_SEARCH_THRESHOLD:
        return "continuation"
    return "broad"


app = FastAPI(title="GenericParser Dynamic Scope Worker", version=VERSION, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": VERSION,
        "runtime": "cloudflare-worker",
        "pagination": "cursor-v1",
        "search_scope": "dynamic-v2",
        "full_threshold": FULL_SEARCH_THRESHOLD,
        "continuation_threshold": CONTINUATION_SEARCH_THRESHOLD,
    }


@app.post("/api/location-id")
async def location_id(payload: cursor.legacy.LocationRequest, request: Request) -> dict[str, int]:
    return await cursor.location_id(payload, request)


@app.post("/api/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    # Correct the shared HTML fallback mapping before the cursor worker builds URLs.
    cursor.legacy._html_page_url = _html_page_url

    reported_total = await scope._reported_total(payload)
    result = await cursor.search(payload, request)
    targeted = scope._is_targeted(payload)
    search_scope = _search_scope(reported_total, targeted)
    broad = search_scope == "broad"

    result["worker"]["version"] = VERSION
    result["worker"]["api_contract"] = "match-v5-dynamic-scope"
    result["worker"]["search_scope"] = "dynamic-v2"
    result["worker"]["html_pagination"] = "one-based-pageNum"

    result["summary"]["reported_total"] = reported_total
    result["summary"]["search_scope"] = search_scope
    result["summary"]["targeted_filters_active"] = targeted
    result["summary"]["full_search_threshold"] = FULL_SEARCH_THRESHOLD
    result["summary"]["continuation_search_threshold"] = CONTINUATION_SEARCH_THRESHOLD
    result["summary"]["loaded_share"] = (
        round(result["summary"]["visible_listings"] / reported_total, 4)
        if reported_total and reported_total > 0 else None
    )

    if broad and payload.cursor_page == 0:
        result["pagination"]["complete"] = True
        result["pagination"]["partial"] = True
        result["pagination"]["continuation_available"] = False
        result["pagination"]["next_page"] = None
        result["pagination"]["stop_reason"] = "broad_search_sample"
        result["summary"]["recommendation"] = (
            "Mehr als 500 Ergebnisse gemeldet. Für eine vollständige Auswertung Pflichtbegriffe, Preis, Ort, "
            "Modell oder einen konkreteren Artikeltitel verwenden."
        )
    else:
        result["summary"]["recommendation"] = None

    return result
