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
    """Projektseitige Beschreibung eines gesuchten Produkts."""

    id: str
    display_name: str
    search_queries: tuple[str, ...]
    brands: tuple[str, ...] = ()
    product_types: tuple[str, ...] = ()
    model_patterns: tuple[str, ...] = ()
    required_any: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()
    max_price: Decimal | None = None
    market_value: Decimal | None = None
    postal_code: str | None = None
    radius_km: int | None = None
    shipping_allowed: bool = True
    accept_bundles: bool = False
    accept_incomplete: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("SearchProfile.id darf nicht leer sein")
        if not self.display_name.strip():
            raise ValueError("SearchProfile.display_name darf nicht leer sein")
        if not self.search_queries:
            raise ValueError("Mindestens eine search_query ist erforderlich")
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
