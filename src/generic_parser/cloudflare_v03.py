from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from . import cloudflare_app as core
from .matching import classify_listing, score_listing, sort_results
from .models import Listing, MatchDecision, MatchResult, SearchProfile
from .sources.kleinanzeigen import FetchedPage, KleinanzeigenBlockedError, KleinanzeigenLayoutError, KleinanzeigenUrlBuilder, extract_location_id

VERSION = "0.32.0"


class SearchRequest(BaseModel):
    mode: Literal["live", "html"] = "live"
    query: str = Field(min_length=2, max_length=120)
    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0, le=200)
    max_results: int | None = Field(default=None, ge=0)
    html: str | None = Field(default=None, max_length=2_000_000)
    required_terms: list[str] = Field(default_factory=list, max_length=30)
    excluded_terms: list[str] = Field(default_factory=list, max_length=30)
    model_patterns: list[str] = Field(default_factory=list, max_length=30)
    brands: list[str] = Field(default_factory=list, max_length=20)
    product_types: list[str] = Field(default_factory=list, max_length=20)
    max_price: Decimal | None = Field(default=None, ge=0)
    market_value: Decimal | None = Field(default=None, ge=0)
    accept_bundles: bool = False
    accept_incomplete: bool = False
    include_review: bool = True
    include_rejected: bool = False
    sort_by: Literal["relevance", "date", "price_asc", "price_desc"] = "relevance"

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Der Suchbegriff ist zu kurz")
        return value

    @field_validator("postal_code")
    @classmethod
    def clean_postal_code(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if len(value) != 5 or not value.isdigit():
            raise ValueError("postal_code muss eine fünfstellige deutsche PLZ sein")
        return value

    @model_validator(mode="after")
    def validate_location(self) -> "SearchRequest":
        if self.mode == "html" and not (self.html or "").strip():
            raise ValueError("Im HTML-Modus muss HTML übergeben werden")
        if any(value is not None for value in (self.postal_code, self.location_id, self.radius_km)):
            if self.postal_code is None or self.location_id is None:
                raise ValueError("Lokale Suchen benötigen PLZ und Location-ID")
        return self


class LocationRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2000)


def _profile(payload: SearchRequest) -> SearchProfile:
    clean = lambda values: tuple(value.strip() for value in values if value.strip())
    return SearchProfile(
        id="cloudflare-mobile",
        display_name="Cloudflare Mobile",
        search_queries=(payload.query,),
        postal_code=payload.postal_code,
        location_id=payload.location_id,
        radius_km=payload.radius_km,
        required_any=clean(payload.required_terms),
        excluded_terms=clean(payload.excluded_terms),
        model_patterns=clean(payload.model_patterns),
        brands=clean(payload.brands),
        product_types=clean(payload.product_types),
        max_price=payload.max_price,
        market_value=payload.market_value,
        accept_bundles=payload.accept_bundles,
        accept_incomplete=payload.accept_incomplete,
    )


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _listing(result: MatchResult) -> dict[str, Any]:
    listing = result.listing
    listing_class, terms = classify_listing(listing)
    return {
        "id": listing.id,
        "title": listing.title,
        "url": listing.url,
        "price": _decimal(listing.price.amount),
        "price_raw": listing.price.raw,
        "price_flags": sorted(flag.value for flag in listing.price.flags),
        "postal_code": listing.location.postal_code,
        "place": listing.location.place,
        "distance_km": _decimal(listing.location.distance_km),
        "posted_at": listing.posted_at.isoformat() if listing.posted_at else None,
        "description": listing.description,
        "source_query": listing.source_query,
        "tags": list(listing.tags),
        "image_url": listing.image_url,
        "score": result.score,
        "decision": result.decision.value,
        "positive_signals": list(result.positive_signals),
        "warnings": list(result.warnings),
        "reason": result.reason,
        "listing_class": listing_class.value,
        "class_terms": list(terms),
        "match": {
            "score": result.score,
            "decision": result.decision.value,
            "positive_signals": list(result.positive_signals),
            "warnings": list(result.warnings),
            "reason": result.reason,
            "listing_class": listing_class.value,
            "class_terms": list(terms),
        },
    }


def _diagnostic(value) -> dict[str, Any]:
    payload = asdict(value)
    payload["state"] = value.state.value
    return payload


def _env(request: Request, name: str) -> str | None:
    env = request.scope.get("env")
    value = getattr(env, name, None) if env is not None else None
    if value is None and isinstance(env, dict):
        value = env.get(name)
    return str(value) if value not in (None, "") else None


def _token(request: Request) -> None:
    expected = _env(request, "APP_TOKEN")
    if expected and request.headers.get("x-genericparser-token", "") != expected:
        raise HTTPException(status_code=401, detail="Zugriffstoken fehlt oder ist ungültig")


app = FastAPI(title="GenericParser Mobile Worker", version=VERSION, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "runtime": "cloudflare-worker"}


@app.post("/api/location-id")
async def location_id(payload: LocationRequest, request: Request) -> dict[str, int]:
    _token(request)
    value = extract_location_id(payload.url)
    if value is None:
        raise HTTPException(status_code=422, detail="Keine Location-ID in der URL gefunden")
    return {"location_id": value}


async def _fetch_all_mobile(payload: SearchRequest):
    """Load mobile API pages until Kleinanzeigen returns a partial or empty page."""
    page_size = min(41, payload.max_results) if payload.max_results else 41
    target = payload.max_results
    headers = {
        "Authorization": f"Basic {core.MOBILE_API_BASIC_AUTH}",
        "User-Agent": "okhttp/4.10.0",
        "Accept": "application/json",
        "X-EBAYK-APP": "genericparser-cloudflare",
    }
    listings = []
    seen: set[str] = set()
    errors = []
    cards = duplicates = pages_loaded = 0
    page_number = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        while True:
            response = await client.get(core._mobile_url(payload, page=page_number, size=page_size), headers=headers)
            if response.status_code in {401, 403, 429}:
                raise KleinanzeigenBlockedError(f"Kleinanzeigen-App-API verweigert den Zugriff ({response.status_code})")
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Kleinanzeigen-App-API antwortet mit HTTP {response.status_code}")
            parsed = core._parse_mobile(response.json(), payload.query, page=page_number)
            pages_loaded += 1
            cards += parsed.diagnostics.cards_found
            errors.extend(parsed.diagnostics.errors)
            if not parsed.listings:
                break
            added = 0
            for listing in parsed.listings:
                if listing.id in seen:
                    duplicates += 1
                    continue
                seen.add(listing.id)
                listings.append(listing)
                added += 1
                if target is not None and len(listings) >= target:
                    break
            if (target is not None and len(listings) >= target) or added == 0 or len(parsed.listings) < page_size:
                break
            page_number += 1
    url = f"mobile-api://pages/{pages_loaded}"
    return core.ParsedPage(tuple(listings), core.PageDiagnostics(core.PageState.RESULTS if listings else core.PageState.NO_RESULTS, url, url, cards, len(listings), duplicates, tuple(errors)))


@app.post("/api/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    _token(request)
    profile = _profile(payload)
    url = KleinanzeigenUrlBuilder().keyword_url(profile, payload.query)
    parser = core.CloudflarePageParser()
    try:
        page = FetchedPage("inline://html", "inline://html", 200, payload.html or "") if payload.mode == "html" else await core.fetch_search_page(url)
        try:
            parsed = parser.parse(page, source_query=payload.query)
        except KleinanzeigenLayoutError:
            if payload.mode != "live":
                raise
            parsed = await _fetch_all_mobile(payload)
        else:
            if payload.mode == "live" and (payload.max_results is None or len(parsed.listings) < payload.max_results):
                mobile = await _fetch_all_mobile(payload)
                if len(mobile.listings) > len(parsed.listings):
                    parsed = mobile
    except KleinanzeigenBlockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except KleinanzeigenLayoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Kleinanzeigen ist nicht erreichbar") from exc

    raw = parsed.listings if payload.max_results is None else parsed.listings[:payload.max_results]
    scored = [score_listing(item, profile) for item in raw]
    alerts = [item for item in scored if item.decision is MatchDecision.ALERT]
    review = [item for item in scored if item.decision is MatchDecision.REVIEW]
    rejected = [item for item in scored if item.decision is MatchDecision.REJECT]
    visible = alerts + (review if payload.include_review else []) + (rejected if payload.include_rejected else [])
    visible = sort_results(visible, payload.sort_by)
    return {
        "mode": payload.mode,
        "generated_urls": [url] if payload.mode == "live" else [],
        "diagnostics": [_diagnostic(parsed.diagnostics)],
        "listings": [_listing(item) for item in visible],
        "summary": {
            "listings": len(visible), "raw_listings": len(raw), "alerts": len(alerts),
            "review": len(review), "rejected": len(rejected),
            "cards": parsed.diagnostics.cards_found,
            "duplicates": parsed.diagnostics.duplicates_skipped,
            "card_errors": len(parsed.diagnostics.errors),
            "truncated": len(parsed.listings) > len(raw),
        },
        "worker": {
            "version": VERSION,
            "single_page": False,
            "fallback": "mobile-api-pagination",
            "matching": "score-v1",
            "api_contract": "match-v1",
            "sort_by": payload.sort_by,
        },
    }
