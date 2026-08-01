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

__version__ = "0.1.0"

__all__ = [
    "ConfigurationError",
    "GenericParser",
    "Listing",
    "ListingSource",
    "Location",
    "MatchDecision",
    "MatchResult",
    "NormalizedPrice",
    "PriceFlag",
    "SearchProfile",
    "compact_text",
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
]
