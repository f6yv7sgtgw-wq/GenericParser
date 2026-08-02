from generic_parser.cloudflare_v039 import VERSION, _html_reported_total, _page_contract


def test_version() -> None:
    assert VERSION == "0.39.1"


def test_html_total_parser_handles_plain_and_more_than_counts() -> None:
    assert _html_reported_total("63 Ergebnisse") == 63
    assert _html_reported_total("Mehr als 10.000 Ergebnisse") == 10000


def test_verified_empty_page_is_complete() -> None:
    result = _page_contract(
        source="html-fallback",
        page=0,
        count=0,
        complete=True,
        stop_reason="empty_page_verified",
        reported_total=0,
        fallback_reason="mobile_and_html_first_page_empty",
        mobile_diagnostics={"http_status": 200, "valid_listings": 0},
    )
    assert result["complete"] is True
    assert result["next_page"] is None
    assert result["fallback_reason"] == "mobile_and_html_first_page_empty"


def test_html_fallback_after_empty_mobile_page_continues() -> None:
    result = _page_contract(
        source="html-fallback",
        page=0,
        count=27,
        complete=False,
        stop_reason="page_complete",
        reported_total=6552,
        fallback_reason="mobile_first_page_empty",
        mobile_diagnostics={
            "http_status": 200,
            "response_bytes": 1234,
            "raw_cards": 0,
            "parsed_listings": 0,
            "valid_listings": 0,
        },
    )
    assert result["complete"] is False
    assert result["next_page"] == 1
    assert result["source"] == "html-fallback"
    assert result["mobile_diagnostics"]["valid_listings"] == 0
