from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from generic_parser import GenericParser, SearchProfile
from generic_parser.sources.kleinanzeigen import (
    FetchedPage,
    KleinanzeigenAdapter,
    KleinanzeigenUrlBuilder,
)

FIXTURE = (Path(__file__).parent / "fixtures" / "kleinanzeigen_results.html").read_text(
    encoding="utf-8"
)
BERLIN = ZoneInfo("Europe/Berlin")


class FakeHttp:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get(self, url: str) -> FetchedPage:
        self.urls.append(url)
        return FetchedPage(url, url, 200, FIXTURE)


def test_adapter_searches_all_queries_and_deduplicates_across_pages() -> None:
    http = FakeHttp()
    adapter = KleinanzeigenAdapter(
        http=http,  # type: ignore[arg-type]
        urls=KleinanzeigenUrlBuilder(sort_by_date=False),
        now_provider=lambda: datetime(2026, 8, 1, 9, 0, tzinfo=BERLIN),
    )
    service = GenericParser(adapter)
    profile = SearchProfile(
        id="evercade",
        display_name="Evercade",
        search_queries=("evercade", "evercade cartridge"),
    )

    listings = service.search(profile)

    assert [item.id for item in listings] == ["10001", "10002"]
    assert len(http.urls) == 2
    assert len(adapter.last_diagnostics) == 2


def test_location_verification_compares_local_and_nationwide_counts() -> None:
    class CountHttp:
        def get(self, url: str) -> FetchedPage:
            if "r5" in url:
                html = FIXTURE.replace(
                    '<article class="aditem" data-adid="10002">',
                    '<div data-removed="10002">',
                )
            else:
                html = FIXTURE
            return FetchedPage(url, url, 200, html)

    adapter = KleinanzeigenAdapter(
        http=CountHttp(),  # type: ignore[arg-type]
        urls=KleinanzeigenUrlBuilder(sort_by_date=False),
        now_provider=lambda: datetime(2026, 8, 1, 9, 0, tzinfo=BERLIN),
    )
    profile = SearchProfile(
        id="local",
        display_name="Local",
        search_queries=("videospiele",),
        postal_code="37075",
        location_id=1234,
        radius_km=50,
    )
    verification = adapter.verify_location_id(profile)
    assert verification.local_cards != verification.nationwide_cards
    assert verification.radius_effective is True
