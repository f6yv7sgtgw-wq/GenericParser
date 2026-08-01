from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from generic_parser import (
    GenericParser,
    Listing,
    Location,
    NormalizedPrice,
    SearchProfile,
)

BERLIN = ZoneInfo("Europe/Berlin")


def make_listing(identifier: str) -> Listing:
    now = datetime(2026, 8, 1, 9, 0, tzinfo=BERLIN)
    return Listing(
        id=identifier,
        title="Testanzeige",
        url=f"https://example.invalid/{identifier}",
        price=NormalizedPrice(raw="10 €", amount=Decimal("10")),
        location=Location(raw="37136 Beispielort", postal_code="37136", place="Beispielort"),
        posted_at=now,
        description=None,
        source_query="test",
        first_seen=now,
        last_seen=now,
    )


class StaticSource:
    def search(self, profile: SearchProfile):
        assert profile.id == "test"
        return (make_listing("1"), make_listing("1"), make_listing("2"))


def test_service_delegates_and_deduplicates() -> None:
    parser = GenericParser(source=StaticSource())
    profile = SearchProfile(id="test", display_name="Test", search_queries=("test",))
    results = parser.search(profile)
    assert [listing.id for listing in results] == ["1", "2"]


def test_service_rejects_invalid_source() -> None:
    with pytest.raises(TypeError, match="ListingSource"):
        GenericParser(source=object())
