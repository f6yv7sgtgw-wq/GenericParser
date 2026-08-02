from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from . import cloudflare_app as core
from .matching import classify_listing, score_listing, sort_results
from .models import Listing, MatchDecision, MatchResult, SearchProfile
from .sources.kleinanzeigen import (
    FetchedPage,
    KleinanzeigenBlockedError,
    KleinanzeigenLayoutError,
    KleinanzeigenUrlBuilder,
    extract_location_id,
)

VERSION = "0.35.3"
SAFETY_PAGE_LIMIT = 100
MOBILE_PAGE_SIZE = 41
MOBILE_REQUEST_PAGE_BUDGET = 6
HTML_REQUEST_PAGE_BUDGET = 3


class SearchRequest(BaseModel):
    mode: Literal["live", "html"] = "live"
    query: str = Field(min_length=2, max_length=120)
    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0, le=200)
    max_results: int | None = Field(default=None, ge=1)
    max_results_explicit: bool = False
    html: str | None = Field(default=None, max_length=2_000_000)
    required_terms: list[str] = Field(default_factory=list, max_length=30)
    excluded_terms: list[str] = Field(default_factory=list, max_length=30)
    model_patterns: list[str] = Field(default_factory=list, max_length=30)
    brands: list[str] = Field(default_factory=list, max_length=20)
    product_types: list[str] = Field(default_factory=list, max_length=20)
    max_price: Decimal | None = Field(default=None, gt=0)
    market_value: Decimal | None = Field(default=None, gt=0)
    accept_bundles: bool = False
    accept_incomplete: bool = False
    include_review: bool = True
    include_rejected: bool = True
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

    @field_validator("required_terms", "excluded_terms", "model_patterns", "brands", "product_types")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip() and value.strip() != "0"]

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


def _effective_limit(payload: SearchRequest) -> int | None:
    return payload.max_results if payload.max_results_explicit else None


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


def _html_page_url(base_url: str, page_number: int) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if page_number <= 0:
        query.pop("pageNum", None)
    else:
        query["pageNum"] = str(page_number)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _pagination(*, source: str, pages_loaded: int, page_size_requested: int | None,
                page_counts: list[int], new_counts: list[int], stop_reason: str,
                unique_listings: int, duplicates: int, payload: SearchRequest,
                request_page_budget: int, fallback_reason: str | None = None) -> dict[str, Any]:
    complete_reasons = {"empty_page", "short_page", "repeated_page", "no_new_ids", "html_mode"}
    return {
        "source": source,
        "pages_loaded": pages_loaded,
        "page_size_requested": page_size_requested,
        "page_counts": page_counts,
        "new_ids_per_page": new_counts,
        "stop_reason": stop_reason,
        "safety_page_limit": SAFETY_PAGE_LIMIT,
        "request_page_budget": request_page_budget,
        "user_limit": _effective_limit(payload),
        "user_limit_explicit": payload.max_results_explicit,
        "unique_listings": unique_listings,
        "duplicates": duplicates,
        "fallback_reason": fallback_reason,
        "complete": stop_reason in complete_reasons,
        "partial": stop_reason == "resource_budget_reached",
    }


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


async def _fetch_mobile(payload: SearchRequest) -> tuple[Any, dict[str, Any]]:
    target = _effective_limit(payload)
    page_size = min(MOBILE_PAGE_SIZE, target) if target else MOBILE_PAGE_SIZE
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
    stop_reason = "resource_budget_reached"

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
        for page_number in range(MOBILE_REQUEST_PAGE_BUDGET):
            response = await client.get(core._mobile_url(payload, page=page_number, size=page_size), headers=headers)
            if response.status_code in {401, 403, 429}:
                raise KleinanzeigenBlockedError(f"Kleinanzeigen-App-API verweigert den Zugriff ({response.status_code})")
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Kleinanzeigen-App-API antwortet mit HTTP {response.status_code}")
            try:
                data = response.json()
            except ValueError as exc:
                raise HTTPException(status_code=502, detail="Kleinanzeigen-App-API lieferte keine gültige JSON-Antwort") from exc
            parsed = core._parse_mobile(data, payload.query, page=page_number)
            pages_loaded += 1
            count = len(parsed.listings)
            page_counts.append(count)
            cards += parsed.diagnostics.cards_found
            errors.extend(parsed.diagnostics.errors)
            if count == 0:
                new_counts.append(0); stop_reason = "empty_page"; break
            signature = tuple(item.id for item in parsed.listings)
            if signature in signatures:
                duplicates += count; new_counts.append(0); stop_reason = "repeated_page"; break
            signatures.add(signature)
            added = 0
            for listing in parsed.listings:
                if listing.id in seen:
                    duplicates += 1; continue
                seen.add(listing.id); listings.append(listing); added += 1
                if target is not None and len(listings) >= target:
                    break
            new_counts.append(added)
            if target is not None and len(listings) >= target:
                stop_reason = "user_limit_reached"; break
            if added == 0:
                stop_reason = "no_new_ids"; break
            if count < page_size:
                stop_reason = "short_page"; break

    marker = f"mobile-api://pages/{pages_loaded}"
    parsed_page = core.ParsedPage(
        tuple(listings),
        core.PageDiagnostics(core.PageState.RESULTS if listings else core.PageState.NO_RESULTS,
                             marker, marker, cards, len(listings), duplicates, tuple(errors)),
    )
    return parsed_page, _pagination(
        source="mobile-api", pages_loaded=pages_loaded, page_size_requested=page_size,
        page_counts=page_counts, new_counts=new_counts, stop_reason=stop_reason,
        unique_listings=len(listings), duplicates=duplicates, payload=payload,
        request_page_budget=MOBILE_REQUEST_PAGE_BUDGET,
    )


async def _fetch_html(payload: SearchRequest, base_url: str, *, fallback_reason: str) -> tuple[Any, dict[str, Any]]:
    target = _effective_limit(payload)
    parser = core.CloudflarePageParser()
    listings: list[Listing] = []
    seen: set[str] = set()
    signatures: set[tuple[str, ...]] = set()
    errors = []
    cards = duplicates = pages_loaded = 0
    page_counts: list[int] = []
    new_counts: list[int] = []
    stop_reason = "resource_budget_reached"

    for page_number in range(HTML_REQUEST_PAGE_BUDGET):
        page = await core.fetch_search_page(_html_page_url(base_url, page_number))
        parsed = parser.parse(page, source_query=payload.query)
        pages_loaded += 1
        count = len(parsed.listings)
        page_counts.append(count)
        cards += parsed.diagnostics.cards_found
        errors.extend(parsed.diagnostics.errors)
        if count == 0:
            new_counts.append(0); stop_reason = "empty_page"; break
        signature = tuple(item.id for item in parsed.listings)
        if signature in signatures:
            duplicates += count; new_counts.append(0); stop_reason = "repeated_page"; break
        signatures.add(signature)
        added = 0
        for listing in parsed.listings:
            if listing.id in seen:
                duplicates += 1; continue
            seen.add(listing.id); listings.append(listing); added += 1
            if target is not None and len(listings) >= target:
                break
        new_counts.append(added)
        if target is not None and len(listings) >= target:
            stop_reason = "user_limit_reached"; break
        if added == 0:
            stop_reason = "no_new_ids"; break

    requested = _html_page_url(base_url, 0)
    parsed_page = core.ParsedPage(
        tuple(listings),
        core.PageDiagnostics(core.PageState.RESULTS if listings else core.PageState.NO_RESULTS,
                             requested, requested, cards, len(listings), duplicates, tuple(errors)),
    )
    return parsed_page, _pagination(
        source="html-fallback", pages_loaded=pages_loaded, page_size_requested=None,
        page_counts=page_counts, new_counts=new_counts, stop_reason=stop_reason,
        unique_listings=len(listings), duplicates=duplicates, payload=payload,
        request_page_budget=HTML_REQUEST_PAGE_BUDGET, fallback_reason=fallback_reason,
    )


@app.post("/api/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    _token(request)
    profile = _profile(payload)
    url = KleinanzeigenUrlBuilder().keyword_url(profile, payload.query)
    parser = core.CloudflarePageParser()

    try:
        if payload.mode == "html":
            page = FetchedPage("inline://html", "inline://html", 200, payload.html or "")
            parsed = parser.parse(page, source_query=payload.query)
            pagination = _pagination(
                source="html", pages_loaded=1, page_size_requested=None,
                page_counts=[len(parsed.listings)], new_counts=[len(parsed.listings)],
                stop_reason="html_mode", unique_listings=len(parsed.listings),
                duplicates=parsed.diagnostics.duplicates_skipped, payload=payload,
                request_page_budget=1,
            )
        else:
            try:
                parsed, pagination = await _fetch_mobile(payload)
                if not parsed.listings:
                    parsed, pagination = await _fetch_html(payload, url, fallback_reason="mobile_empty")
            except (KleinanzeigenBlockedError, HTTPException, httpx.RequestError, KleinanzeigenLayoutError) as exc:
                parsed, pagination = await _fetch_html(
                    payload, url, fallback_reason=f"{type(exc).__name__}: {exc}"
                )
    except KleinanzeigenBlockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except KleinanzeigenLayoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Kleinanzeigen ist nicht erreichbar") from exc

    effective_limit = _effective_limit(payload)
    raw = parsed.listings if effective_limit is None else parsed.listings[:effective_limit]
    scored = [score_listing(item, profile) for item in raw]
    alerts = [item for item in scored if item.decision is MatchDecision.ALERT]
    review = [item for item in scored if item.decision is MatchDecision.REVIEW]
    rejected = [item for item in scored if item.decision is MatchDecision.REJECT]
    visible = alerts + (review if payload.include_review else []) + (rejected if payload.include_rejected else [])
    visible = sort_results(visible, payload.sort_by)

    fetched_count = len(parsed.listings)
    scored_count = len(scored)
    visible_count = len(visible)
    return {
        "mode": payload.mode,
        "generated_urls": [url] if payload.mode == "live" else [],
        "diagnostics": [_diagnostic(parsed.diagnostics)],
        "pagination": pagination,
        "listings": [_listing(item) for item in visible],
        "summary": {
            "listings": visible_count,
            "raw_listings": scored_count,
            "fetched_listings": fetched_count,
            "scored_listings": scored_count,
            "visible_listings": visible_count,
            "hidden_by_filter": scored_count - visible_count,
            "alerts": len(alerts), "review": len(review), "rejected": len(rejected),
            "cards": parsed.diagnostics.cards_found,
            "duplicates": pagination.get("duplicates", parsed.diagnostics.duplicates_skipped),
            "card_errors": len(parsed.diagnostics.errors),
            "truncated": effective_limit is not None and fetched_count > scored_count,
            "pages_loaded": pagination.get("pages_loaded", 0),
            "stop_reason": pagination.get("stop_reason", "unknown"),
            "source": pagination.get("source", "unknown"),
            "requested_user_limit": payload.max_results,
            "effective_user_limit": effective_limit,
            "user_limit_explicit": payload.max_results_explicit,
            "page_size_requested": pagination.get("page_size_requested"),
            "data_consistent": fetched_count == pagination.get("unique_listings", fetched_count),
            "partial_due_to_resource_budget": pagination.get("partial", False),
        },
        "worker": {
            "version": VERSION,
            "single_page": False,
            "primary_source": "mobile-api",
            "source_used": pagination.get("source", "unknown"),
            "fallback": "resource-bounded-html-on-mobile-failure-or-empty",
            "matching": "score-v1-non-destructive-default",
            "api_contract": "match-v3-resource-budget",
            "sort_by": payload.sort_by,
        },
    }
