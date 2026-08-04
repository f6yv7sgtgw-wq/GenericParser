"""Öffentliche API des GenericParser-Pakets."""

from .config import ConfigurationError, load_profile, load_profiles, profile_from_dict, profile_to_dict, save_profile, save_profiles
from .models import Listing, Location, MatchDecision, MatchResult, NormalizedPrice, PriceFlag, SearchProfile
from .normalization import compact_text, normalize_text, parse_location, parse_posted_at, parse_price
from .service import GenericParser, ListingSource
from .sources.kleinanzeigen import FetchedPage, KleinanzeigenAdapter, KleinanzeigenBlockedError, KleinanzeigenHttpClient, KleinanzeigenLayoutError, LocationVerification, KleinanzeigenPageParser, KleinanzeigenUrlBuilder, PageDiagnostics, PageState, extract_location_id, slugify_keyword

__version__ = "0.44.6.1"

__all__ = [
    "ConfigurationError", "GenericParser", "FetchedPage", "KleinanzeigenAdapter",
    "KleinanzeigenBlockedError", "KleinanzeigenHttpClient", "KleinanzeigenLayoutError",
    "LocationVerification", "KleinanzeigenPageParser", "KleinanzeigenUrlBuilder",
    "PageDiagnostics", "PageState", "Listing", "ListingSource", "Location",
    "MatchDecision", "MatchResult", "NormalizedPrice", "PriceFlag", "SearchProfile",
    "compact_text", "load_profile", "load_profiles", "normalize_text", "parse_location",
    "parse_posted_at", "parse_price", "profile_from_dict", "profile_to_dict",
    "save_profile", "save_profiles", "extract_location_id", "slugify_keyword",
]
