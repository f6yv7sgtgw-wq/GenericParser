from generic_parser.cloudflare_v039 import (
    MAX_PAGE,
    MOBILE_PAGE_SIZE,
    VERSION,
    SearchRequest,
    _html_reported_total,
    _page_contract,
)


def test_version_and_page_worker_contract() -> None:
    assert VERSION == "0.39.0"
    assert MOBILE_PAGE_SIZE == 41
    assert MAX_PAGE >= 100


def test_request_defaults_to_first_page() -> None:
    payload = SearchRequest(query="evercade")
    assert payload.page == 0
    assert payload.source == "auto"


def test_page_contract_exposes_next_page() -> None:
    result = _page_contract(
        source="html-fallback", page=2, count=27, complete=False,
        stop_reason="page_complete", reported_total=63,
    )
    assert result["worker_unit"] == "one-page"
    assert result["pages_loaded"] == 1
    assert result["next_page"] == 3
    assert result["continuation_available"] is True


def test_complete_page_has_no_cursor() -> None:
    result = _page_contract(
        source="mobile-api", page=1, count=10, complete=True,
        stop_reason="short_page", reported_total=51,
    )
    assert result["next_page"] is None
    assert result["complete"] is True


def test_html_total_detection() -> None:
    assert _html_reported_total("63 Ergebnisse") == 63
    assert _html_reported_total("Mehr als 10.000 Ergebnisse") == 10000
    assert _html_reported_total('{"totalResultCount":6552}') == 6552


def test_html_total_detection_returns_none_without_count() -> None:
    assert _html_reported_total("Keine Anzahl vorhanden") is None
