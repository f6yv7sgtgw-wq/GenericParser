from __future__ import annotations

import json
from pathlib import Path

from generic_parser.module_api_v2 import listing_to_v2
from generic_parser.normalization import (
    CONDITION_CODES,
    DELIVERY_MODES,
    normalize_condition,
    normalize_delivery_mode,
)


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_condition_phrases_map_onto_source_neutral_codes():
    assert normalize_condition("Neu mit Etikett") == "new"
    assert normalize_condition("Neu/OVP") == "new"
    assert normalize_condition("New without tags") == "new"
    assert normalize_condition("gebraucht") == "used"
    assert normalize_condition("Zufriedenstellend") == "used"
    assert normalize_condition("defekt, nur für Bastler") == "defective"
    assert normalize_condition("Zustand offen") == "unknown"
    assert normalize_condition(None, "") == "unknown"
    assert set(CONDITION_CODES) >= {"new", "like_new", "used", "defective", "unknown"}


def test_like_new_is_its_own_code_instead_of_counting_as_new_or_used():
    # Bis 1.7.1 leitete der Browser "wie neu" auf 'new' und "Sehr gut" auf
    # 'used' um - beides über eine Regex auf dem Anzeigetext.
    assert normalize_condition("wie neu") == "like_new"
    assert normalize_condition("Sehr gut") == "like_new"
    assert normalize_condition("Very good") == "like_new"
    assert normalize_condition("neuwertig") == "like_new"


def test_a_defect_wins_over_a_new_sounding_phrase():
    assert normalize_condition("Neu, aber defekt") == "defective"
    assert normalize_condition("Wie neu, Ersatzteil") == "defective"


def test_delivery_mode_is_derived_once_instead_of_in_every_client():
    assert normalize_delivery_mode(shipping_available=False, shipping_cost=0) == "pickup"
    assert normalize_delivery_mode(shipping_available=True, shipping_cost=0) == "free"
    assert normalize_delivery_mode(shipping_available=True, shipping_cost=4.9) == "available"
    assert normalize_delivery_mode(shipping_available=True) == "available"
    assert normalize_delivery_mode() == "unknown"
    assert normalize_delivery_mode(shipping_cost="keine Zahl") == "unknown"
    assert set(DELIVERY_MODES) == {"free", "available", "pickup", "unknown"}


def test_module_v2_carries_both_codes_additively():
    listing = listing_to_v2(
        {
            "id": "vinted:1",
            "title": "Kleid",
            "url": "https://www.vinted.de/items/1",
            "source": "vinted",
            "result_info": {"condition": "wie neu"},
            "shipping_available": True,
            "shipping_cost": 0,
        },
        "vinted",
    )
    # Der Anzeigetext der Quelle bleibt unangetastet.
    assert listing["condition"] == "wie neu"
    assert listing["condition_code"] == "like_new"
    assert listing["delivery"]["mode"] == "free"
    assert listing["delivery"]["shipping_available"] is True


def test_sources_without_a_condition_report_unknown_rather_than_guessing():
    listing = listing_to_v2(
        {
            "id": "kleinanzeigen:3",
            "title": "Buch",
            "url": "https://www.kleinanzeigen.de/s-anzeige/3",
            "source": "kleinanzeigen",
            "shipping_available": False,
        },
        "kleinanzeigen",
    )
    assert listing["condition_code"] == "unknown"
    assert listing["delivery"]["mode"] == "pickup"


def test_openapi_documents_both_additive_fields():
    schema = json.loads(read("docs/openapi-module-v2.json"))["components"]["schemas"]["Listing"]
    assert schema["properties"]["condition_code"]["enum"] == list(CONDITION_CODES)
    assert schema["properties"]["delivery"]["properties"]["mode"]["enum"] == list(DELIVERY_MODES)
    assert "condition_code" not in schema.get("required", [])


def test_browser_filters_on_the_code_and_only_falls_back_to_text():
    app_js = read("cloudflare/public/app.js")
    html = read("cloudflare/public/index.html")
    assert "const CONDITION_CODES=['new','like_new','used','defective','unknown'];" in app_js
    assert "if(CONDITION_CODES.includes(code))return code;" in app_js
    assert "const mode=String(x?.delivery_mode||'');" in app_js
    assert "condition_code:item.condition_code,delivery_mode:delivery.mode" in app_js
    # Ohne eigene Filteroption würde "wie neu" nach der Trennung unsichtbar.
    assert '<option value="like_new">Wie neu</option>' in html


def test_vinted_catalog_cards_carry_their_photo():
    worker = read("pocs/vinted-browser/src/index.js")
    # Ohne Bild im Katalogtreffer warten die Kacheln auf die Detailwarteschlange.
    assert "function imageFrom(window)" in worker
    assert "image_url:imageFrom(after)||imageFrom(before)" in worker


def test_bundle_lines_become_items_but_shipping_and_reference_prices_do_not():
    from generic_parser.kleinanzeigen_bundles import parse_bundle_items

    items = parse_bundle_items(
        "Verkaufe folgende N64-Spiele einzeln:\n"
        "- Zelda Ocarina of Time 25€\n"
        "- Mario Kart 64 20 €\n"
        "1x Super Mario 64 – 15,00 EUR\n"
        "Versand 5 € extra\n"
        "Neupreis war 60 €\n"
        "Gesamt 90€\n"
    )
    assert [item["title"] for item in items] == [
        "Zelda Ocarina of Time",
        "Mario Kart 64",
        "Super Mario 64",
    ]
    assert [item["price"] for item in items] == [25.0, 20.0, 15.0]


def test_a_description_without_a_real_list_stays_a_bundle():
    from generic_parser.kleinanzeigen_bundles import parse_bundle_items

    assert parse_bundle_items("Konvolut, alles zusammen 90 €") == []
    assert parse_bundle_items("Sammlung mit vielen Spielen, Preis VB") == []
    # Eine Preisspanne in einer Zeile ist mehrdeutig und ergibt keinen Artikel.
    assert parse_bundle_items("Spiel A 10 € bis 20 €\nSpiel B 15 €") == []


def test_derived_tiles_point_at_the_original_advert_and_never_invent_a_url():
    from generic_parser.kleinanzeigen_bundles import derive_listings

    parent = {
        "id": "kleinanzeigen:123",
        "url": "https://www.kleinanzeigen.de/s-anzeige/123",
        "image_url": "https://example.invalid/bild.jpg",
        "result_info": {"condition": "gebraucht", "scope": "Bundle/Konvolut"},
    }
    derived = derive_listings(parent, [{"title": "Zelda", "price": 25.0}, {"title": "Mario", "price": 20.0}])
    assert [row["id"] for row in derived] == ["kleinanzeigen:123#item-1", "kleinanzeigen:123#item-2"]
    assert all(row["url"] == parent["url"] for row in derived)
    assert all(row["derived_from"] == "kleinanzeigen:123" for row in derived)
    assert all(row["result_info"]["scope"] == "Einzelangebot" for row in derived)
    assert derived[0]["price"] == 25.0


def test_resolution_replaces_only_resolvable_bundles_and_fails_open():
    import asyncio

    from generic_parser.kleinanzeigen_bundles import resolve_bundles

    resolvable = {
        "id": "kleinanzeigen:1",
        "url": "https://www.kleinanzeigen.de/s-anzeige/1",
        "product_classification": {"code": "bundle"},
    }
    broken = {
        "id": "kleinanzeigen:2",
        "url": "https://www.kleinanzeigen.de/s-anzeige/2",
        "product_classification": {"code": "bundle"},
    }
    single = {"id": "kleinanzeigen:3", "url": "https://www.kleinanzeigen.de/s-anzeige/3"}

    async def fetch(url: str) -> str:
        if url.endswith("/1"):
            return '<div id="viewad-description-text">Zelda 25 €\nMario Kart 20 €</div>'
        raise RuntimeError("Detailseite nicht erreichbar")

    result = asyncio.run(resolve_bundles([resolvable, broken, single], fetch_html=fetch))
    ids = [row["id"] for row in result["listings"]]
    assert ids == ["kleinanzeigen:1#item-1", "kleinanzeigen:1#item-2", "kleinanzeigen:2", "kleinanzeigen:3"]
    assert result["stats"]["resolved"] == 1
    assert result["stats"]["failed"] == 1
    assert result["stats"]["derived"] == 2


def test_only_classified_bundles_cost_a_detail_request():
    import asyncio

    from generic_parser.kleinanzeigen_bundles import resolve_bundles

    calls: list[str] = []

    async def fetch(url: str) -> str:
        calls.append(url)
        return ""

    listings = [{"id": f"kleinanzeigen:{i}", "url": f"https://www.kleinanzeigen.de/s-anzeige/{i}"} for i in range(5)]
    asyncio.run(resolve_bundles(listings, fetch_html=fetch))
    assert calls == []


def test_module_v2_marks_a_derived_listing_without_touching_the_bundle_flag():
    listing = listing_to_v2(
        {
            "id": "kleinanzeigen:1#item-1",
            "title": "Zelda",
            "url": "https://www.kleinanzeigen.de/s-anzeige/1",
            "source": "kleinanzeigen",
            "derived_from": "kleinanzeigen:1",
            "price": 25.0,
        },
        "kleinanzeigen",
    )
    assert listing["offer"]["derived_from"] == "kleinanzeigen:1"
    assert listing["offer"]["bundle"] is False
    assert listing_to_v2({"id": "x", "title": "t", "url": "u", "source": "ebay"}, "ebay")["offer"]["derived_from"] is None


def test_search_mask_keeps_active_filters_visible_when_the_panel_collapses():
    html = read("cloudflare/public/index.html")
    css = read("cloudflare/public/ui-180.css")
    # Nur das Raster klappt ein; Kopfzeile und aktive Chips stehen davor.
    assert '<div class="filter-body" id="filter-body">' in html
    body_start = html.index('<div class="filter-body"')
    assert html.index('id="active-result-filters"') < body_start
    assert ".result-filters-180 .filter-body {\n  display: none;\n}" in css
    assert ".result-filters-180.is-open .filter-body {" in css
    # Der Umschalter trug das Panel bisher nur mobil.
    assert ".results-heading-actions .mobile-filter-toggle {" in css


def test_new_browser_assets_are_wired_and_precached():
    html = read("cloudflare/public/index.html")
    worker = read("cloudflare/public/service-worker.js")
    assert './ui-180.css' in html and './ui-180.js' in html
    assert html.index("ui-162.css") < html.index("ui-180.css")
    # Ohne Precache liefert der Service Worker die neue Ebene nicht mit aus.
    assert '"./ui-180.css",' in worker
    assert '"./ui-180.js",' in worker


def test_a_per_unit_filler_does_not_end_up_in_the_derived_title():
    from generic_parser.kleinanzeigen_bundles import parse_bundle_items

    items = parse_bundle_items(
        "Extreme-G 2 je 15€\nZelda à 25 €\nMario Kart pro Stück 20€\nTurok Stk. 12 €\n"
    )
    assert [item["title"] for item in items] == [
        "Extreme-G 2",
        # Das führende \s+ im Füllwortmuster verhindert, dass "à" das
        # Schluss-a von "Zelda" verschluckt.
        "Zelda",
        "Mario Kart",
        "Turok",
    ]


def test_a_per_unit_price_line_is_still_no_article():
    from generic_parser.kleinanzeigen_bundles import parse_bundle_items

    items = parse_bundle_items("Preis pro Stück 20 €\nArtikel B 9 €\nArtikel C 8 €")
    assert [item["title"] for item in items] == ["Artikel B", "Artikel C"]


def test_derived_from_names_the_parent_as_a_listing_key():
    bare = listing_to_v2(
        {
            "id": "kleinanzeigen:1#item-1",
            "title": "Zelda",
            "url": "https://www.kleinanzeigen.de/s-anzeige/1",
            "source": "kleinanzeigen",
            "derived_from": "3482755595",
        },
        "kleinanzeigen",
    )
    already_keyed = listing_to_v2(
        {
            "id": "kleinanzeigen:1#item-2",
            "title": "Mario",
            "url": "https://www.kleinanzeigen.de/s-anzeige/1",
            "source": "kleinanzeigen",
            "derived_from": "kleinanzeigen:3482755595",
        },
        "kleinanzeigen",
    )
    assert bare["offer"]["derived_from"] == "kleinanzeigen:3482755595"
    assert already_keyed["offer"]["derived_from"] == "kleinanzeigen:3482755595"
