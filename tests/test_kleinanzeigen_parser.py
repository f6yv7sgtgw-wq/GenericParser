from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from generic_parser.sources.kleinanzeigen import (
    FetchedPage,
    KleinanzeigenBlockedError,
    KleinanzeigenLayoutError,
    KleinanzeigenPageParser,
    PageState,
)

FIXTURES = Path(__file__).parent / "fixtures"
BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 8, 1, 9, 0, tzinfo=BERLIN)


def page(name: str, *, status: int = 200) -> FetchedPage:
    return FetchedPage(
        requested_url="https://www.kleinanzeigen.de/s-test/k0",
        final_url="https://www.kleinanzeigen.de/s-test/k0",
        status_code=status,
        text=(FIXTURES / name).read_text(encoding="utf-8"),
    )


def test_parse_realistic_result_cards_and_deduplicate_top_ad() -> None:
    result = KleinanzeigenPageParser().parse(
        page("kleinanzeigen_results.html"), source_query="evercade", now=NOW
    )

    assert result.diagnostics.state is PageState.RESULTS
    assert result.diagnostics.cards_found == 4
    assert result.diagnostics.listings_parsed == 2
    assert result.diagnostics.duplicates_skipped == 1
    assert len(result.diagnostics.errors) == 1

    first, second = result.listings
    assert first.id == "10001"
    assert first.price.amount == Decimal("30")
    assert first.location.postal_code == "37075"
    assert first.location.distance_km == Decimal("8")
    assert first.posted_at == datetime(2026, 8, 1, 8, 5, tzinfo=BERLIN)
    assert first.tags == ("Versand möglich",)
    assert first.image_url == "https://img.kleinanzeigen.de/api/v1/prod-ads/images/aa.jpg"
    assert first.url.startswith("https://www.kleinanzeigen.de/s-anzeige/")

    assert second.price.amount == Decimal("1250.50")
    assert second.posted_at == datetime(2026, 7, 31, 22, 10, tzinfo=BERLIN)
    assert second.image_url == "https://www.kleinanzeigen.de/static/zelda.jpg"


def test_no_results_is_normal_state() -> None:
    result = KleinanzeigenPageParser().parse(
        page("kleinanzeigen_no_results.html"), source_query="nichts", now=NOW
    )
    assert result.listings == ()
    assert result.diagnostics.state is PageState.NO_RESULTS


def test_unknown_layout_raises_maintenance_error() -> None:
    with pytest.raises(KleinanzeigenLayoutError, match="Keine Ergebniskarten"):
        KleinanzeigenPageParser().parse(
            page("kleinanzeigen_layout_changed.html"), source_query="test", now=NOW
        )


def test_blocked_page_is_detected() -> None:
    with pytest.raises(KleinanzeigenBlockedError):
        KleinanzeigenPageParser().parse(
            page("kleinanzeigen_blocked.html"), source_query="test", now=NOW
        )
