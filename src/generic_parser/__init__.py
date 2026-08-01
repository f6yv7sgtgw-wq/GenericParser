"""Öffentliche API des GenericParser-Pakets."""

from .config import (
    ConfigurationError,
    load_profile,
    load_profiles,
    profile_from_dict,
    profile_to_dict,
    save_profile,
    save_profiles,
)
from .models import (
    Listing,
    Location,
    MatchDecision,
    MatchResult,
    NormalizedPrice,
    PriceFlag,
    SearchProfile,
)
from .normalization import compact_text, normalize_text, parse_location, parse_posted_at, parse_price
from .service import GenericParser, ListingSource
from .sources.kleinanzeigen import (
    FetchedPage,
    KleinanzeigenAdapter,
    KleinanzeigenBlockedError,
    KleinanzeigenHttpClient,
    KleinanzeigenLayoutError,
    KleinanzeigenPageParser,
    KleinanzeigenUrlBuilder,
    LocationVerification,
    PageDiagnostics,
    PageState,
    extract_location_id,
    slugify_keyword,
)

__version__ = "0.2.0a1"

__all__ = [
    "ConfigurationError",
    "FetchedPage",
    "GenericParser",
    "KleinanzeigenAdapter",
    "KleinanzeigenBlockedError",
    "KleinanzeigenHttpClient",
    "KleinanzeigenLayoutError",
    "KleinanzeigenPageParser",
    "KleinanzeigenUrlBuilder",
    "Listing",
    "ListingSource",
    "Location",
    "LocationVerification",
    "MatchDecision",
    "MatchResult",
    "NormalizedPrice",
    "PageDiagnostics",
    "PageState",
    "PriceFlag",
    "SearchProfile",
    "compact_text",
    "extract_location_id",
    "load_profile",
    "load_profiles",
    "normalize_text",
    "parse_location",
    "parse_posted_at",
    "parse_price",
    "profile_from_dict",
    "profile_to_dict",
    "save_profile",
    "save_profiles",
    "slugify_keyword",
]
