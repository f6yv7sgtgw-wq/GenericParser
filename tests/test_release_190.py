"""Relevanzprüfung 1.9.0: Deckung der Suchbegriffe als additive Ampelregel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generic_parser.relevance import (
    RULESET,
    apply_relevance_evaluation,
    evaluate_relevance,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/normalization_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["relevance"], ids=lambda case: case["name"])
def test_relevance_fixtures(case):
    result = evaluate_relevance(case["query"], case["title"], case.get("description"))
    assert result["verdict"] == case["expected"], result


def test_result_is_additive_and_explainable():
    result = evaluate_relevance("super mario kart 8", "Mario Party 8")
    assert result["ruleset"] == RULESET
    assert 0.0 <= result["score"] <= 1.0
    assert result["matched_terms"] == ["mario"]
    assert result["missing_terms"] == ["kart", "8"]
    assert set(result["terms"]) == {"mario", "kart", "8"}
    # „super" ist Füllwort und taucht in keiner Liste auf.
    assert "super" not in result["terms"]


def test_description_counts_weaker_than_the_title():
    in_title = evaluate_relevance("mario kart 8", "Mario Kart 8 Deluxe")
    in_description = evaluate_relevance(
        "mario kart 8", "Nintendo Konvolut", "Mario Kart 8 Deluxe und mehr"
    )
    assert in_title["score"] > in_description["score"]
    assert in_description["score"] > 0.0


def test_a_query_of_only_filler_words_still_checks_something():
    result = evaluate_relevance("neu original", "Gebrauchtes Fahrrad")
    assert result["terms"] == ["neu", "original"]
    assert result["verdict"] == "mismatch"


def test_an_empty_query_never_flags_anything():
    result = evaluate_relevance("", "Mario Kart 8 Deluxe")
    assert result["verdict"] == "match"
    assert result["score"] == 1.0


def _green_evaluation() -> dict:
    return {
        "color": "green",
        "label": "🟢 Passend",
        "score": 90,
        "decision": "accept",
        "reason": "Alle Kriterien erfüllt",
        "criteria": [],
        "active_criteria": 0,
    }


def test_mismatch_turns_the_light_red_but_does_not_remove_the_listing():
    relevance = evaluate_relevance("super mario kart 8", "Super Mario Odyssey")
    evaluation = apply_relevance_evaluation(_green_evaluation(), relevance)
    assert evaluation["color"] == "red"
    assert evaluation["decision"] == "reject"
    criterion = evaluation["criteria"][-1]
    assert criterion["name"] == "Relevanz"
    assert criterion["hard"] is True
    # Kein Feld, das den Treffer verschwinden ließe: Die Sichtbarkeit
    # entscheidet weiterhin allein der Statusfilter (keine stille Kürzung).
    assert evaluation["active_criteria"] == len(evaluation["criteria"])


def test_partial_coverage_becomes_a_review_case():
    relevance = evaluate_relevance("super mario kart 8", "Mario Kart Wii")
    evaluation = apply_relevance_evaluation(_green_evaluation(), relevance)
    assert evaluation["color"] == "yellow"
    assert evaluation["decision"] == "review"
    assert evaluation["criteria"][-1]["hard"] is False


def test_a_full_match_leaves_the_evaluation_untouched():
    relevance = evaluate_relevance("super mario kart 8", "Mario Kart 8 Deluxe")
    before = _green_evaluation()
    evaluation = apply_relevance_evaluation(before, relevance)
    assert evaluation["color"] == "green"
    assert evaluation["decision"] == "accept"
    assert evaluation["criteria"] == []


def test_an_existing_red_light_is_not_upgraded_by_a_review_verdict():
    red = {
        "color": "red",
        "label": "🔴 Unpassend",
        "score": 0,
        "decision": "reject",
        "reason": "Produktart passt nicht",
        "criteria": [{"name": "Produktart", "color": "red", "hard": True, "active": True}],
        "active_criteria": 1,
    }
    relevance = evaluate_relevance("super mario kart 8", "Mario Kart Wii")
    evaluation = apply_relevance_evaluation(red, relevance)
    assert evaluation["color"] == "red"
    assert evaluation["decision"] == "reject"
    assert "Produktart passt nicht" in evaluation["reason"]
    assert "Suchbegriffe" in evaluation["reason"]


def test_decorated_listings_carry_the_relevance_field():
    from generic_parser.search_service_v0450 import SearchRequest, _decorate_listing

    payload = SearchRequest(query="super mario kart 8")
    listing = {
        "title": "Mario Party 8",
        "description": "Partyspiel für die Wii",
        "price": {"raw": "20 €", "amount": 20.0},
    }
    decorated = _decorate_listing(listing, payload)
    relevance = decorated["relevance"]
    assert relevance["ruleset"] == RULESET
    assert relevance["verdict"] == "mismatch"
    assert decorated["traffic_light"]["color"] == "red"
    assert decorated["match"]["decision"] == "reject"
    # Additiv: Die bestehenden Verträge bleiben unberührt.
    assert "product_classification" in decorated
    assert any(c["name"] == "Relevanz" for c in decorated["traffic_light"]["criteria"])


def test_a_matching_listing_stays_green_after_decoration():
    from generic_parser.search_service_v0450 import SearchRequest, _decorate_listing

    payload = SearchRequest(query="super mario kart 8")
    listing = {
        "title": "Mario Kart 8 Deluxe Nintendo Switch",
        "description": "Sehr guter Zustand, mit OVP",
        "price": {"raw": "35 €", "amount": 35.0},
    }
    decorated = _decorate_listing(listing, payload)
    assert decorated["relevance"]["verdict"] == "match"
    assert decorated["traffic_light"]["color"] != "red"
