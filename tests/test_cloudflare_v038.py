from generic_parser.cloudflare_v038 import (
    BROAD_SEARCH_THRESHOLD,
    CONTINUATION_SEARCH_THRESHOLD,
    FULL_SEARCH_THRESHOLD,
    VERSION,
    _html_page_url,
    _search_scope,
)


def test_version_and_thresholds() -> None:
    assert VERSION == "0.38.0"
    assert FULL_SEARCH_THRESHOLD == 100
    assert CONTINUATION_SEARCH_THRESHOLD == 500
    assert BROAD_SEARCH_THRESHOLD == 500


def test_small_search_is_complete() -> None:
    assert _search_scope(63, False) == "complete"


def test_medium_search_uses_continuation() -> None:
    assert _search_scope(101, False) == "continuation"
    assert _search_scope(500, False) == "continuation"


def test_large_search_is_broad_sample() -> None:
    assert _search_scope(501, False) == "broad"
    assert _search_scope(6552, False) == "broad"


def test_targeted_search_is_not_sampled() -> None:
    assert _search_scope(6552, True) == "targeted"


def test_html_page_mapping_skips_duplicate_first_page() -> None:
    base = "https://www.kleinanzeigen.de/s-evercade/k0?sortingField=SORTING_DATE"
    assert "pageNum=" not in _html_page_url(base, 0)
    assert "pageNum=2" in _html_page_url(base, 1)
    assert "pageNum=3" in _html_page_url(base, 2)
