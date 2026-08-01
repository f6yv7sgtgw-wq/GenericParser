"""Optionaler Live-Smoke-Test.

Nur explizit mit GENERIC_PARSER_LIVE_TEST=1 ausführen. Der Test prüft keine
bestimmte Trefferzahl, weil echte Anzeigen veränderlich sind. Er bestätigt nur,
dass eine aktuelle Kleinanzeigen-Ergebnisliste ohne Block-/Layoutfehler verarbeitet
werden kann.
"""

import os

import pytest

from generic_parser import GenericParser, SearchProfile
from generic_parser.sources.kleinanzeigen import KleinanzeigenAdapter, KleinanzeigenHttpClient

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    os.environ.get("GENERIC_PARSER_LIVE_TEST") != "1",
    reason="Live-Test nur explizit aktivieren",
)
def test_live_search_page_can_be_processed() -> None:
    profile = SearchProfile(
        id="live-smoke",
        display_name="Live Smoke Test",
        search_queries=("zelda link to the past snes",),
    )
    with KleinanzeigenHttpClient(max_attempts=1) as http:
        adapter = KleinanzeigenAdapter(http=http)
        listings = GenericParser(adapter).search(profile)
    assert adapter.last_diagnostics
    assert all(item.id and item.url for item in listings)
