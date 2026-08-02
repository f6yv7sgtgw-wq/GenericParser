from generic_parser.cloudflare_v03 import (
    HTML_REQUEST_PAGE_BUDGET,
    MOBILE_REQUEST_PAGE_BUDGET,
    SAFETY_PAGE_LIMIT,
    VERSION,
    SearchRequest,
    _effective_limit,
    _html_page_url,
    _pagination,
)


def test_version_and_resource_limits() -> None:
    assert VERSION == "0.35.3"
    assert SAFETY_PAGE_LIMIT == 100
    assert MOBILE_REQUEST_PAGE_BUDGET == 6
    assert HTML_REQUEST_PAGE_BUDGET == 3


def test_empty_result_limit_is_not_effective() -> None:
    payload = SearchRequest(query="evercade")
    assert payload.max_results is None
    assert payload.max_results_explicit is False
    assert _effective_limit(payload) is None


def test_result_limit_only_applies_when_explicit() -> None:
    restored = SearchRequest(query="evercade", max_results=27)
    explicit = SearchRequest(query="evercade", max_results=27, max_results_explicit=True)
    assert _effective_limit(restored) is None
    assert _effective_limit(explicit) == 27


def test_all_matching_classes_are_visible_by_default() -> None:
    payload = SearchRequest(query="evercade")
    assert payload.include_review is True
    assert payload.include_rejected is True


def test_html_pagination_uses_page_num_without_losing_filters() -> None:
    base = "https://www.kleinanzeigen.de/s-evercade/k0?sortierung=preis"
    first = _html_page_url(base, 0)
    third = _html_page_url(base, 2)
    assert "sortierung=preis" in first
    assert "pageNum=" not in first
    assert "sortierung=preis" in third
    assert "pageNum=2" in third


def test_resource_budget_result_is_partial_and_consistent() -> None:
    payload = SearchRequest(query="snes")
    result = _pagination(
        source="mobile-api",
        pages_loaded=6,
        page_size_requested=41,
        page_counts=[41, 41, 41, 41, 41, 41],
        new_counts=[41, 41, 40, 41, 39, 41],
        stop_reason="resource_budget_reached",
        unique_listings=243,
        duplicates=3,
        payload=payload,
        request_page_budget=6,
    )
    assert result["partial"] is True
    assert result["complete"] is False
    assert result["unique_listings"] == sum(result["new_ids_per_page"])


def test_natural_end_is_complete() -> None:
    payload = SearchRequest(query="evercade")
    result = _pagination(
        source="mobile-api",
        pages_loaded=2,
        page_size_requested=41,
        page_counts=[41, 12],
        new_counts=[41, 12],
        stop_reason="short_page",
        unique_listings=53,
        duplicates=0,
        payload=payload,
        request_page_budget=6,
    )
    assert result["complete"] is True
    assert result["partial"] is False


def test_explicit_user_limit_is_transparent() -> None:
    payload = SearchRequest(query="evercade", max_results=50, max_results_explicit=True)
    result = _pagination(
        source="mobile-api",
        pages_loaded=2,
        page_size_requested=41,
        page_counts=[41, 41],
        new_counts=[41, 9],
        stop_reason="user_limit_reached",
        unique_listings=50,
        duplicates=0,
        payload=payload,
        request_page_budget=6,
    )
    assert result["user_limit"] == 50
    assert result["user_limit_explicit"] is True
    assert result["partial"] is False
