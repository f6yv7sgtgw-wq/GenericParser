from generic_parser.cloudflare_v036 import (
    HTML_PAGE_BUDGET,
    MAX_CURSOR_PAGE,
    MOBILE_PAGE_BUDGET,
    VERSION,
    SearchRequest,
    _chunk_pagination,
)


def test_version_and_resource_budgets() -> None:
    assert VERSION == "0.36.0"
    assert MOBILE_PAGE_BUDGET == 4
    assert HTML_PAGE_BUDGET == 2
    assert MAX_CURSOR_PAGE >= 100


def test_first_request_starts_automatically() -> None:
    payload = SearchRequest(query="snes")
    assert payload.cursor_page == 0
    assert payload.cursor_source == "auto"
    assert payload.max_results is None
    assert payload.max_results_explicit is False


def test_cursor_request_can_continue_mobile_source() -> None:
    payload = SearchRequest(query="snes", cursor_page=4, cursor_source="mobile-api")
    assert payload.cursor_page == 4
    assert payload.cursor_source == "mobile-api"


def test_incomplete_chunk_exposes_next_cursor() -> None:
    result = _chunk_pagination(
        source="mobile-api",
        start_page=4,
        pages_loaded=4,
        page_counts=[41, 41, 41, 41],
        new_counts=[41, 40, 41, 39],
        duplicates=3,
        stop_reason="chunk_budget_reached",
        complete=False,
    )
    assert result["next_page"] == 8
    assert result["continuation_available"] is True
    assert result["partial"] is True
    assert result["unique_listings"] == 161


def test_complete_chunk_has_no_cursor() -> None:
    result = _chunk_pagination(
        source="html-fallback",
        start_page=6,
        pages_loaded=1,
        page_counts=[0],
        new_counts=[0],
        duplicates=0,
        stop_reason="empty_page",
        complete=True,
    )
    assert result["next_page"] is None
    assert result["continuation_available"] is False
    assert result["complete"] is True


def test_explicit_limit_is_preserved_per_chunk() -> None:
    payload = SearchRequest(query="snes", max_results=25, max_results_explicit=True)
    assert payload.max_results == 25
    assert payload.max_results_explicit is True
