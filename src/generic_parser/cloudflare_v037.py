from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import httpx
from fastapi import FastAPI, Request

from . import cloudflare_app as core
from . import cloudflare_v036 as cursor

VERSION = "0.37.0"
BROAD_SEARCH_THRESHOLD = 1000

SearchRequest = cursor.SearchRequest


def _extract_reported_total(value: Any) -> int | None:
    candidate_keys = {
        "total", "totalcount", "total_count", "totalresultcount", "totalresults",
        "numfound", "numberofresults", "resultcount", "counttotal",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "").replace("_", "")
            if normalized in candidate_keys and isinstance(item, (int, float)) and item >= 0:
                return int(item)
        for item in value.values():
            found = _extract_reported_total(item)
            if found is not None:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            found = _extract_reported_total(item)
            if found is not None:
                return found
    return None


def _is_targeted(payload: SearchRequest) -> bool:
    return any(
        (
            payload.postal_code,
            payload.location_id,
            payload.radius_km,
            payload.max_price,
            payload.market_value,
            payload.required_terms,
            payload.excluded_terms,
            payload.model_patterns,
            payload.brands,
            payload.product_types,
            payload.max_results_explicit,
        )
    )


async def _reported_total(payload: SearchRequest) -> int | None:
    if payload.mode != "live" or payload.cursor_page != 0 or payload.cursor_source == "html-fallback":
        return None
    headers = {
        "Authorization": f"Basic {core.MOBILE_API_BASIC_AUTH}",
        "User-Agent": "okhttp/4.10.0",
        "Accept": "application/json",
        "X-EBAYK-APP": "genericparser-cloudflare",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
            response = await client.get(core._mobile_url(payload, page=0, size=1), headers=headers)
        if response.status_code >= 400:
            return None
        return _extract_reported_total(response.json())
    except (httpx.RequestError, ValueError, TypeError):
        return None


app = FastAPI(title="GenericParser Scope Worker", version=VERSION, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": VERSION,
        "runtime": "cloudflare-worker",
        "pagination": "cursor-v1",
        "search_scope": "broad-vs-targeted-v1",
    }


@app.post("/api/location-id")
async def location_id(payload: cursor.legacy.LocationRequest, request: Request) -> dict[str, int]:
    return await cursor.location_id(payload, request)


@app.post("/api/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    reported_total = await _reported_total(payload)
    result = await cursor.search(payload, request)
    targeted = _is_targeted(payload)
    broad = reported_total is not None and reported_total >= BROAD_SEARCH_THRESHOLD and not targeted

    result["worker"]["version"] = VERSION
    result["worker"]["api_contract"] = "match-v4-scope"
    result["worker"]["search_scope"] = "broad-vs-targeted-v1"
    result["summary"]["reported_total"] = reported_total
    result["summary"]["loaded_share"] = (
        round(result["summary"]["visible_listings"] / reported_total, 4)
        if reported_total and reported_total > 0 else None
    )
    result["summary"]["search_scope"] = "broad" if broad else "targeted"
    result["summary"]["targeted_filters_active"] = targeted

    if broad and payload.cursor_page == 0:
        result["pagination"]["complete"] = True
        result["pagination"]["partial"] = True
        result["pagination"]["continuation_available"] = False
        result["pagination"]["next_page"] = None
        result["pagination"]["stop_reason"] = "broad_search_sample"
        result["summary"]["recommendation"] = (
            "Die Suche ist sehr breit. Pflichtbegriffe, Preis, Kategorie, Ort oder ein konkreter Artikeltitel "
            "verwenden, um den Suchraum vollständig auszuwerten."
        )
    else:
        result["summary"]["recommendation"] = None

    return result
