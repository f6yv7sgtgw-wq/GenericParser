from generic_parser.cloudflare_v03 import SearchRequest


def test_empty_optional_fields_are_absent_or_none():
    payload = SearchRequest(query="snes")
    assert payload.max_results is None
    assert payload.required_terms == []
    assert payload.brands == []


def test_explicit_limit_still_supported():
    payload = SearchRequest(query="snes", max_results=250)
    assert payload.max_results == 250
