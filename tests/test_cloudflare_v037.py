from generic_parser.cloudflare_v037 import (
    BROAD_SEARCH_THRESHOLD,
    VERSION,
    SearchRequest,
    _extract_reported_total,
    _is_targeted,
)


def test_version_and_threshold() -> None:
    assert VERSION == "0.37.0"
    assert BROAD_SEARCH_THRESHOLD == 1000


def test_extract_reported_total_from_nested_mobile_payload() -> None:
    payload = {"ads": {"pagination": {"totalResultCount": 6552}}}
    assert _extract_reported_total(payload) == 6552


def test_extract_reported_total_accepts_num_found() -> None:
    assert _extract_reported_total({"meta": {"numFound": 184}}) == 184


def test_plain_keyword_search_is_not_targeted() -> None:
    payload = SearchRequest(query="snes")
    assert _is_targeted(payload) is False


def test_required_term_makes_search_targeted() -> None:
    payload = SearchRequest(query="snes", required_terms=["konsole"])
    assert _is_targeted(payload) is True


def test_explicit_limit_makes_search_targeted() -> None:
    payload = SearchRequest(query="snes", max_results=100, max_results_explicit=True)
    assert _is_targeted(payload) is True
