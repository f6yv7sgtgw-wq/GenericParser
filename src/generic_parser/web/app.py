from __future__ import annotations

import os
import re
import threading
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator, model_validator

from ..models import Listing, SearchProfile
from ..normalization import BERLIN
from ..sources.kleinanzeigen import (
    FetchedPage,
    KleinanzeigenBlockedError,
    KleinanzeigenHttpClient,
    KleinanzeigenLayoutError,
    KleinanzeigenPageParser,
    KleinanzeigenUrlBuilder,
    PageDiagnostics,
    extract_location_id,
)

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
BUNDLED_FIXTURE_DIR = PACKAGE_DIR / "fixtures"
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


class SearchRequest(BaseModel):
    mode: Literal["live", "fixture", "html"] = "fixture"
    query: str = Field(min_length=1, max_length=160)
    category_path: str | None = Field(default=None, max_length=180)
    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0, le=200)
    max_price: Decimal | None = Field(default=None, ge=0)
    fixture_name: str | None = None
    html: str | None = Field(default=None, max_length=2_000_000)
    save_fixture: bool = False

    @field_validator("query", "category_path", "postal_code", "fixture_name", "html", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 5 or not value.isdigit()):
            raise ValueError("Die PLZ muss fünfstellig sein")
        return value

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "SearchRequest":
        if self.mode == "fixture" and not self.fixture_name:
            raise ValueError("Für den Fixture-Modus ist eine Fixture-Datei erforderlich")
        if self.mode == "html" and not self.html:
            raise ValueError("Für den HTML-Modus muss HTML eingefügt werden")
        if self.mode == "live":
            local_values = (self.postal_code, self.location_id, self.radius_km)
            if any(value is not None for value in local_values) and (
                self.postal_code is None or self.location_id is None
            ):
                raise ValueError("Lokale Suchen benötigen PLZ und verifizierte Location-ID")
        return self


class LocationRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1000)


class VerifyLocationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=160)
    postal_code: str = Field(pattern=r"^\d{5}$")
    location_id: int = Field(gt=0)
    radius_km: int = Field(default=5, ge=1, le=200)


class FixtureStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def save(self, page: FetchedPage, *, query: str) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(BERLIN).strftime("%Y%m%d-%H%M%S")
        safe_query = _SAFE_NAME_RE.sub("-", query).strip("-._")[:60] or "search"
        filename = f"{timestamp}-{safe_query}.html"
        path = self.directory / filename
        path.write_text(page.text, encoding="utf-8")
        return filename


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


def _profile_from_request(payload: SearchRequest) -> SearchProfile:
    try:
        max_price = Decimal(str(payload.max_price)) if payload.max_price is not None else None
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail="Ungültiger Maximalpreis") from exc
    return SearchProfile(
        id="web-diagnostic",
        display_name="Web-Diagnose",
        search_queries=(payload.query,),
        category_paths=(payload.category_path,) if payload.category_path else (),
        postal_code=payload.postal_code,
        location_id=payload.location_id,
        radius_km=payload.radius_km,
        max_price=max_price,
    )


def _deduplicate(listings: list[Listing]) -> list[Listing]:
    seen: set[str] = set()
    result: list[Listing] = []
    for listing in listings:
        if listing.id in seen:
            continue
        seen.add(listing.id)
        result.append(listing)
    return result


def create_app(*, fixture_store_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(
        title="GenericParser Diagnose",
        version="0.2.0b1",
        description="Manuelle Kleinanzeigen-Tests, Fixture-Parsing und Parserdiagnose.",
    )
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    store_dir = Path(
        fixture_store_dir
        or os.environ.get("GENERIC_PARSER_FIXTURE_DIR", "data/fixtures")
    )
    fixture_store = FixtureStore(store_dir)
    live_lock = threading.Lock()

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"version": "0.2.0b1"},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.2.0b1"}

    @app.get("/api/fixtures")
    def fixtures() -> dict[str, list[str]]:
        names = sorted(path.name for path in BUNDLED_FIXTURE_DIR.glob("*.html"))
        return {"fixtures": names}

    @app.post("/api/location-id")
    def location_id(payload: LocationRequest) -> dict[str, int]:
        value = extract_location_id(payload.url)
        if value is None:
            raise HTTPException(status_code=422, detail="Keine Location-ID in der URL gefunden")
        return {"location_id": value}

    @app.post("/api/search")
    def search(payload: SearchRequest) -> dict[str, Any]:
        parser = KleinanzeigenPageParser()
        saved_fixtures: list[str] = []
        diagnostics: list[PageDiagnostics] = []
        listings: list[Listing] = []
        generated_urls: list[str] = []

        try:
            if payload.mode == "fixture":
                fixture_path = BUNDLED_FIXTURE_DIR / Path(payload.fixture_name or "").name
                if not fixture_path.is_file():
                    raise HTTPException(status_code=404, detail="Fixture nicht gefunden")
                uri = fixture_path.resolve().as_uri()
                page = FetchedPage(uri, uri, 200, fixture_path.read_text(encoding="utf-8"))
                parsed = parser.parse(page, source_query=payload.query)
                listings.extend(parsed.listings)
                diagnostics.append(parsed.diagnostics)

            elif payload.mode == "html":
                page = FetchedPage("inline://html", "inline://html", 200, payload.html or "")
                parsed = parser.parse(page, source_query=payload.query)
                listings.extend(parsed.listings)
                diagnostics.append(parsed.diagnostics)

            else:
                if not live_lock.acquire(blocking=False):
                    raise HTTPException(
                        status_code=409,
                        detail="Eine Live-Suche läuft bereits. Bitte erst danach erneut starten.",
                    )
                try:
                    profile = _profile_from_request(payload)
                    builder = KleinanzeigenUrlBuilder()
                    with KleinanzeigenHttpClient(
                        request_delay_range=(1.0, 2.0),
                        retry_wait_seconds=1.0,
                        blocked_backoff_seconds=5.0,
                        max_attempts=2,
                    ) as http:
                        for source_query, url in builder.urls_for(profile):
                            generated_urls.append(url)
                            page = http.get(url)
                            if payload.save_fixture:
                                saved_fixtures.append(fixture_store.save(page, query=source_query))
                            parsed = parser.parse(page, source_query=source_query)
                            listings.extend(parsed.listings)
                            diagnostics.append(parsed.diagnostics)
                finally:
                    live_lock.release()

        except KleinanzeigenBlockedError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except KleinanzeigenLayoutError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except HTTPException:
            raise
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensiver API-Rand
            raise HTTPException(status_code=502, detail=f"Suche fehlgeschlagen: {exc}") from exc

        result = _deduplicate(listings)
        return {
            "mode": payload.mode,
            "generated_urls": generated_urls,
            "saved_fixtures": saved_fixtures,
            "diagnostics": [_diagnostic_dict(item) for item in diagnostics],
            "listings": [_listing_dict(item) for item in result],
            "summary": {
                "listings": len(result),
                "cards": sum(item.cards_found for item in diagnostics),
                "duplicates": sum(item.duplicates_skipped for item in diagnostics),
                "card_errors": sum(len(item.errors) for item in diagnostics),
            },
        }

    @app.post("/api/verify-location")
    def verify_location(payload: VerifyLocationRequest) -> dict[str, Any]:
        if not live_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="Eine Live-Suche läuft bereits")
        try:
            profile = SearchProfile(
                id="location-check",
                display_name="Location-Prüfung",
                search_queries=(payload.query,),
                postal_code=payload.postal_code,
                location_id=payload.location_id,
                radius_km=payload.radius_km,
            )
            builder = KleinanzeigenUrlBuilder()
            local_url = builder.keyword_url(profile, payload.query)
            nationwide = SearchProfile(
                id="location-check-national",
                display_name="Bundesweite Prüfung",
                search_queries=(payload.query,),
            )
            nationwide_url = builder.keyword_url(nationwide, payload.query)
            parser = KleinanzeigenPageParser()
            with KleinanzeigenHttpClient(
                request_delay_range=(1.0, 2.0),
                retry_wait_seconds=1.0,
                blocked_backoff_seconds=5.0,
                max_attempts=2,
            ) as http:
                local = parser.parse(http.get(local_url), source_query=payload.query)
                national = parser.parse(http.get(nationwide_url), source_query=payload.query)
            return {
                "local_cards": local.diagnostics.cards_found,
                "nationwide_cards": national.diagnostics.cards_found,
                "radius_effective": local.diagnostics.cards_found != national.diagnostics.cards_found,
                "local_url": local_url,
                "nationwide_url": nationwide_url,
            }
        except KleinanzeigenBlockedError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except KleinanzeigenLayoutError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            live_lock.release()

    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = os.environ.get("GENERIC_PARSER_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("GENERIC_PARSER_PORT", "8000")))
    uvicorn.run("generic_parser.web.app:app", host=host, port=port, reload=False)
