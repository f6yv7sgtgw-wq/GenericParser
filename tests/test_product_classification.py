from __future__ import annotations

from generic_parser.product_classification import (
    apply_classification_evaluation,
    apply_classification_metadata,
    classify_listing,
)


def classify(title: str, query: str = "Super Mario Kart 8", **extra):
    return classify_listing({"title": title, **extra}, query)


def test_known_junk_from_production_search_is_rejected_as_merchandise():
    examples = [
        "Level 8 Super Mario Kartenspiel Ravensburger NEU",
        "Jakks Super Mario Kart Yoshi in Mach 8 - NEU",
        "CARRERA Pull & Speed Super Mario Kart Mach 8 Mario 1:43",
    ]
    for title in examples:
        result = classify(title)
        assert result["code"] == "related_merchandise"
        assert result["relevance"] == "reject"


def test_evercade_snes_and_platform_games_are_main_products():
    examples = [
        ("Evercade Interplay Collection 1 Cartridge", "Interplay Collection 1"),
        ("Super Mario Kart SNES PAL Modul", "Super Mario Kart"),
        ("Mario Kart 8 Deluxe Nintendo Switch", "Mario Kart 8 Deluxe"),
    ]
    for title, query in examples:
        result = classify(title, query)
        assert result["code"] == "main_product"
        assert result["relevance"] == "accept"


def test_ebay_category_can_identify_a_video_game_without_platform_in_title():
    result = classify(
        "Super Mario Kart 8 Deluxe",
        category_path="Video Games & Consoles > Video Games",
    )
    assert result["code"] == "main_product"
    assert result["confidence"] == "high"


def test_accessories_bundles_wanted_rental_and_service_are_distinct():
    cases = {
        "Super Mario Kart Leerhülle ohne Spiel": "accessory_part",
        "Super Mario Kart Spielepaket 5 Spiele": "bundle",
        "Suche dringend Super Mario Kart 8": "wanted",
        "Nintendo Switch Vermietung mit Mario Kart": "rental",
        "Nintendo Reparaturservice und Umbau Service": "service",
    }
    for title, expected in cases.items():
        assert classify(title)["code"] == expected


def test_unknown_product_is_review_instead_of_false_green():
    classification = classify("Super Mario")
    assert classification["code"] == "unknown"
    assert classification["relevance"] == "review"
    listing = {"title": "Super Mario", "result_info": {}}
    apply_classification_metadata(listing, classification)
    evaluation = apply_classification_evaluation(
        {
            "color": "green",
            "label": "Passender Treffer",
            "score": 100,
            "decision": "accept",
            "reason": "Suchbegriff gefunden",
            "criteria": [],
        },
        classification,
    )
    assert evaluation["color"] == "yellow"
    assert evaluation["decision"] == "review"
    assert evaluation["criteria"][0]["name"] == "Produktart"


def test_merchandise_hard_reject_overrides_old_green_evaluation():
    classification = classify("CARRERA Super Mario Kart Mach 8")
    evaluation = apply_classification_evaluation(
        {
            "color": "green",
            "label": "Passender Treffer",
            "score": 100,
            "decision": "accept",
            "reason": "Suchbegriff gefunden",
            "criteria": [],
        },
        classification,
    )
    assert evaluation["color"] == "red"
    assert evaluation["decision"] == "reject"
    assert evaluation["score"] == 0


def test_query_for_accessory_does_not_reject_the_requested_product_type():
    result = classify(
        "Evercade Ersatzhülle ohne Spiel",
        query="Evercade Ersatzhülle",
    )
    assert result["code"] == "accessory_part"
    assert result["relevance"] == "accept"
