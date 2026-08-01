from decimal import Decimal

import pytest

from generic_parser import SearchProfile
from generic_parser.sources.kleinanzeigen import (
    KleinanzeigenUrlBuilder,
    extract_location_id,
    slugify_keyword,
)


def test_slugify_keyword_transliterates_umlauts() -> None:
    assert slugify_keyword("  Zelda Größe Ä  ") == "zelda-groesse-ae"


def test_extract_location_id() -> None:
    assert extract_location_id("https://www.kleinanzeigen.de/s-nrw/test/k0l928r50") == 928
    assert extract_location_id("https://www.kleinanzeigen.de/s-test/k0") is None


def test_build_nationwide_keyword_url() -> None:
    profile = SearchProfile(id="x", display_name="X", search_queries=("A Link to the Past",))
    url = KleinanzeigenUrlBuilder().keyword_url(profile, profile.search_queries[0])
    assert url == (
        "https://www.kleinanzeigen.de/s-a-link-to-the-past/k0"
        "?sortingField=SORTING_DATE"
    )


def test_build_local_keyword_url_with_verified_location_id() -> None:
    profile = SearchProfile(
        id="x",
        display_name="X",
        search_queries=("Evercade",),
        postal_code="37075",
        location_id=1234,
        radius_km=50,
    )
    url = KleinanzeigenUrlBuilder().keyword_url(profile, "Evercade")
    assert "/s-37075/evercade/k0l1234r50" in url


def test_build_category_url() -> None:
    profile = SearchProfile(
        id="x",
        display_name="X",
        category_paths=("s-videospiele",),
        location_id=928,
        radius_km=100,
    )
    url = KleinanzeigenUrlBuilder(sort_by_date=False).category_url(profile, "s-videospiele")
    assert url == "https://www.kleinanzeigen.de/s-videospiele/k0l928r100"


def test_radius_never_uses_postal_code_as_location_id() -> None:
    profile = SearchProfile(
        id="x",
        display_name="X",
        search_queries=("Evercade",),
        postal_code="37075",
        radius_km=50,
    )
    with pytest.raises(ValueError, match="location_id"):
        KleinanzeigenUrlBuilder().keyword_url(profile, "Evercade")


def test_category_only_profile_is_valid() -> None:
    profile = SearchProfile(
        id="category",
        display_name="Kategorie",
        category_paths=("s-videospiele",),
        max_price=Decimal("50"),
    )
    assert not profile.search_queries


def test_keyword_location_id_without_postal_code_is_rejected() -> None:
    profile = SearchProfile(
        id="x",
        display_name="X",
        search_queries=("Evercade",),
        location_id=1234,
        radius_km=50,
    )
    with pytest.raises(ValueError, match="postal_code"):
        KleinanzeigenUrlBuilder().keyword_url(profile, "Evercade")
