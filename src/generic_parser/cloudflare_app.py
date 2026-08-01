from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable, Literal

import httpx
from bs4 import BeautifulSoup, SoupStrainer, Tag
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from .models import Listing, SearchProfile
from .normalization import BERLIN
from .sources.kleinanzeigen import (
    CardParseError,
    FetchedPage,
    KleinanzeigenBlockedError,
    KleinanzeigenHttpClient,
    KleinanzeigenLayoutError,
    KleinanzeigenPageParser,
    KleinanzeigenUrlBuilder,
    PageDiagnostics,
    PageState,
    ParsedPage,
    extract_location_id,
)

VERSION = "0.2.0rc1"
FetchPage = Callable[[str], Awaitable[FetchedPage]]


class CloudSearchRequest(BaseModel):
    mode: Literal["live", "html"] = "live"
    query: str = Field(min_length=2, max_length=120)
    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0, le=200)
    max_results: int = Field(default=12, ge=1, le=20)
    html: str | None = Field(default=None, max_length=2_000_000)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Der Suchbegriff ist zu kurz")
        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if len(value) != 5 or not value.isdigit():
            raise ValueError("postal_code muss eine fünfstellige deutsche PLZ sein")
        return value

    @model_validator(mode="after")
    def validate_mode_and_location(self) -> "CloudSearchRequest":
        if self.mode == "html" and not (self.html or "").strip():
            raise ValueError("Im HTML-Modus muss HTML übergeben werden")
        local_values = (self.postal_code, self.location_id, self.radius_km)
        if any(value is not None for value in local_values):
            if self.postal_code is None or self.location_id is None:
                raise ValueError("Lokale Suchen benötigen PLZ und Location-ID")
        return self


class LocationRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2000)


class CloudflarePageParser(KleinanzeigenPageParser):
    """CPU-sparsame Ergebnislistenvariante für Cloudflare Workers."""

    def parse(
        self,
        page: FetchedPage,
        *,
        source_query: str,
        now: datetime | None = None,
    ) -> ParsedPage:
        if page.status_code in {403, 429} or KleinanzeigenHttpClient._looks_blocked(page.text):
            raise KleinanzeigenBlockedError("Geblockte oder Challenge-Seite erkannt")

        soup = BeautifulSoup(page.text, "html.parser", parse_only=SoupStrainer("article"))
        cards = soup.select("article.aditem")
        if not cards:
            state = self._empty_state(page.text)
            diagnostics = PageDiagnostics(
                state=state,
                requested_url=page.requested_url,
                final_url=page.final_url,
                cards_found=0,
                listings_parsed=0,
                duplicates_skipped=0,
            )
            if state is PageState.LAYOUT_CHANGED:
                raise KleinanzeigenLayoutError("Keine Ergebniskarten und kein Nulltreffer-Hinweis")
            return ParsedPage(listings=(), diagnostics=diagnostics)

        reference = now or datetime.now(BERLIN)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=BERLIN)
        else:
            reference = reference.astimezone(BERLIN)

        seen: set[str] = set()
        listings: list[Listing] = []
        errors: list[CardParseError] = []
        duplicates = 0
        for index, card in enumerate(cards):
            listing_id = card.get("data-adid") if isinstance(card, Tag) else None
            try:
                listing = self._parse_card(card, source_query=source_query, now=reference)
            except (TypeError, ValueError, AttributeError) as exc:
                errors.append(CardParseError(index=index, listing_id=listing_id, message=str(exc)))
                continue
            if listing.id in seen:
                duplicates += 1
                continue
            seen.add(listing.id)
            listings.append(listing)

        if cards and not listings:
            raise KleinanzeigenLayoutError("Alle Ergebniskarten konnten nicht geparst werden")
        return ParsedPage(
            listings=tuple(listings),
            diagnostics=PageDiagnostics(
                state=PageState.RESULTS,
                requested_url=page.requested_url,
                final_url=page.final_url,
                cards_found=len(cards),
                listings_parsed=len(listings),
                duplicates_skipped=duplicates,
                errors=tuple(errors),
            ),
        )


async def fetch_search_page(url: str) -> FetchedPage:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
        "Cache-Control": "no-cache",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers=headers)
    page = FetchedPage(
        requested_url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        text=response.text,
    )
    if response.status_code in {403, 429} or KleinanzeigenHttpClient._looks_blocked(response.text):
        raise KleinanzeigenBlockedError(f"Kleinanzeigen blockiert den Abruf ({response.status_code})")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Kleinanzeigen antwortet mit HTTP {response.status_code}")
    return page


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _listing_dict(listing: Listing) -> dict[str, Any]:
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
    }


def _diagnostic_dict(diagnostic: PageDiagnostics) -> dict[str, Any]:
    payload = asdict(diagnostic)
    payload["state"] = diagnostic.state.value
    return payload


def _env_value(request: Request, name: str) -> str | None:
    env = request.scope.get("env")
    if env is None:
        return None
    value = getattr(env, name, None)
    if value is None and isinstance(env, dict):
        value = env.get(name)
    return str(value) if value not in (None, "") else None


def _require_token(request: Request) -> None:
    expected = _env_value(request, "APP_TOKEN")
    if expected is None:
        return
    supplied = request.headers.get("x-genericparser-token", "")
    if supplied != expected:
        raise HTTPException(status_code=401, detail="Zugriffstoken fehlt oder ist ungültig")


def create_cloudflare_app(*, fetcher: FetchPage = fetch_search_page) -> FastAPI:
    app = FastAPI(
        title="GenericParser Mobile Worker",
        version=VERSION,
        description="Mobile Kleinanzeigen-Diagnose für Cloudflare Workers.",
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": VERSION, "runtime": "cloudflare-worker"}

    @app.post("/api/location-id")
    async def location_id(payload: LocationRequest, request: Request) -> dict[str, int]:
        _require_token(request)
        value = extract_location_id(payload.url)
        if value is None:
            raise HTTPException(status_code=422, detail="Keine Location-ID in der URL gefunden")
        return {"location_id": value}

    @app.post("/api/search")
    async def search(payload: CloudSearchRequest, request: Request) -> dict[str, Any]:
        _require_token(request)
        profile = SearchProfile(
            id="cloudflare-mobile",
            display_name="Cloudflare Mobile",
            search_queries=(payload.query,),
            postal_code=payload.postal_code,
            location_id=payload.location_id,
            radius_km=payload.radius_km,
        )
        url = KleinanzeigenUrlBuilder().keyword_url(profile, payload.query)
        parser = CloudflarePageParser()
        try:
            if payload.mode == "html":
                page = FetchedPage("inline://html", "inline://html", 200, payload.html or "")
            else:
                page = await fetcher(url)
            parsed = parser.parse(page, source_query=payload.query)
        except KleinanzeigenBlockedError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except KleinanzeigenLayoutError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Kleinanzeigen ist nicht erreichbar") from exc

        listings = parsed.listings[: payload.max_results]
        return {
            "mode": payload.mode,
            "generated_urls": [url] if payload.mode == "live" else [],
            "diagnostics": [_diagnostic_dict(parsed.diagnostics)],
            "listings": [_listing_dict(item) for item in listings],
            "summary": {
                "listings": len(listings),
                "cards": parsed.diagnostics.cards_found,
                "duplicates": parsed.diagnostics.duplicates_skipped,
                "card_errors": len(parsed.diagnostics.errors),
                "truncated": len(parsed.listings) > len(listings),
            },
            "worker": {
                "version": VERSION,
                "single_page": True,
                "max_results": payload.max_results,
            },
        }

    return app


app = create_cloudflare_app()
