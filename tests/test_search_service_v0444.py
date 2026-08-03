from types import SimpleNamespace

from generic_parser.search_service_v0444 import _evaluate


def payload(**overrides):
    values = {
        "query": "Evercade",
        "required_terms": [],
        "excluded_terms": [],
        "model_patterns": [],
        "brands": [],
        "max_price": None,
        "market_value": None,
        "accept_bundles": True,
        "accept_incomplete": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def listing(title="Evercade Tomb Raider Collection 1", **info):
    return {
        "title": title,
        "price": 25,
        "result_info": {
            "offer_type": info.get("offer_type", "Spiel/Cartridge"),
            "condition": info.get("condition", "Zustand offen"),
            "scope": info.get("scope", "Einzelangebot"),
        },
    }


def test_empty_optional_fields_are_not_evaluated():
    result = _evaluate(listing(), payload())
    names = {criterion["name"] for criterion in result["criteria"]}
    assert names == {"Suchbegriff"}
    assert result["color"] == "green"


def test_required_and_excluded_terms_are_independent():
    result = _evaluate(
        listing("Evercade Blaze Cartridge"),
        payload(required_terms=["Blaze"], excluded_terms=["defekt"]),
    )
    colors = {criterion["name"]: criterion["color"] for criterion in result["criteria"]}
    assert colors["Pflichtbegriffe"] == "green"
    assert colors["Ausschlussbegriffe"] == "green"


def test_missing_required_term_is_red_even_without_excluded_terms():
    result = _evaluate(listing(), payload(required_terms=["Blaze"]))
    assert result["color"] == "red"
    assert any(c["name"] == "Pflichtbegriffe" and c["color"] == "red" for c in result["criteria"])


def test_unknown_condition_is_ignored_but_detected_defect_is_active():
    unknown = _evaluate(listing(condition="Zustand offen"), payload(accept_incomplete=False))
    assert "Zustand" not in {criterion["name"] for criterion in unknown["criteria"]}

    defective = _evaluate(listing(condition="defekt/unvollständig"), payload(accept_incomplete=False))
    assert defective["color"] == "red"
    assert any(c["name"] == "Zustand" for c in defective["criteria"])


def test_empty_price_fields_do_not_create_price_rules():
    result = _evaluate(listing(), payload(max_price=None, market_value=None))
    names = {criterion["name"] for criterion in result["criteria"]}
    assert "Maximalpreis" not in names
    assert "Richtwert" not in names
