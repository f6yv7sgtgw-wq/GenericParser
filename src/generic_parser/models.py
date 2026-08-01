from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class PriceFlag(str, Enum):
    """Zusätzliche Bedeutung eines normalisierten Preises."""

    NEGOTIABLE = "verhandelbar"
    FREE = "gratis"
    UNKNOWN = "preis_unbekannt"
    SUSPICIOUS_LOW = "verdaechtig_niedrig"


@dataclass(frozen=True, slots=True)
class NormalizedPrice:
    raw: str
    amount: Decimal | None
    flags: frozenset[PriceFlag] = field(default_factory=frozenset)

    @property
    def is_known(self) -> bool:
        return self.amount is not None

    @property
    def is_free(self) -> bool:
        return PriceFlag.FREE in self.flags


@dataclass(frozen=True, slots=True)
class Location:
    raw: str
    postal_code: str | None
    place: str
    distance_km: Decimal | None = None


@dataclass(frozen=True, slots=True)
class SearchProfile:
    """Projektseitige Beschreibung eines gesuchten Produkts.

    ``location_id`` ist die interne Kleinanzeigen-Orts-ID. Eine PLZ darf
    niemals still als Location-ID interpretiert werden.
    """

    id: str
    display_name: str
    search_queries: tuple[str, ...] = ()
    category_paths: tuple[str, ...] = ()
    brands: tuple[str, ...] = ()
    product_types: tuple[str, ...] = ()
    model_patterns: tuple[str, ...] = ()
    required_any: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()
    max_price: Decimal | None = None
    market_value: Decimal | None = None
    postal_code: str | None = None
    location_id: int | None = None
    radius_km: int | None = None
    shipping_allowed: bool = True
    accept_bundles: bool = False
    accept_incomplete: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("SearchProfile.id darf nicht leer sein")
        if not self.display_name.strip():
            raise ValueError("SearchProfile.display_name darf nicht leer sein")
        if not self.search_queries and not self.category_paths:
            raise ValueError("Mindestens eine search_query oder ein category_path ist erforderlich")
        if self.postal_code is not None and (
            len(self.postal_code) != 5 or not self.postal_code.isdigit()
        ):
            raise ValueError("postal_code muss eine fünfstellige deutsche PLZ sein")
        if self.location_id is not None and self.location_id <= 0:
            raise ValueError("location_id muss positiv sein")
        if self.radius_km is not None and self.radius_km < 0:
            raise ValueError("radius_km darf nicht negativ sein")
        if self.max_price is not None and self.max_price < 0:
            raise ValueError("max_price darf nicht negativ sein")
        if self.market_value is not None and self.market_value < 0:
            raise ValueError("market_value darf nicht negativ sein")


@dataclass(frozen=True, slots=True)
class Listing:
    """Quellenunabhängige Darstellung einer Kleinanzeigen-Anzeige."""

    id: str
    title: str
    url: str
    price: NormalizedPrice
    location: Location
    posted_at: datetime | None
    description: str | None
    source_query: str
    first_seen: datetime
    last_seen: datetime
    tags: tuple[str, ...] = ()
    image_url: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Listing.id darf nicht leer sein")
        if not self.title.strip():
            raise ValueError("Listing.title darf nicht leer sein")
        if not self.url.startswith(("https://", "http://")):
            raise ValueError("Listing.url muss absolut sein")
        if self.last_seen < self.first_seen:
            raise ValueError("last_seen darf nicht vor first_seen liegen")


class MatchDecision(str, Enum):
    ALERT = "alert"
    REVIEW = "review"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class MatchResult:
    listing: Listing
    profile: SearchProfile
    score: int
    decision: MatchDecision
    positive_signals: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reason: str = ""
    detail_page_loaded: bool = False
    should_alert: bool = False
