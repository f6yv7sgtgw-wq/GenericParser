from __future__ import annotations

import json
from pathlib import Path

from generic_parser import vinted_adapter
from generic_parser.module_api_v2 import listing_to_v2
from generic_parser.vinted_enrichment import _DETAIL_FIELDS, _merge_listing


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_vinted_api_item_carries_the_catalog_size():
    listing = vinted_adapter._normalize_api(
        {
            "id": 4711,
            "title": "King Louie Kleid",
            "url": "/items/4711-king-louie",
            "price": "39,90",
            "status": "Sehr gut",
            "size_title": " M ",
        },
        "King Louie",
    )
    assert listing is not None
    assert listing["result_info"]["size"] == "M"
    assert listing["result_info"]["display_text"] == "Vinted · wie neu · Größe M · Einzelangebot"


def test_unknown_size_stays_none_instead_of_a_filler_label():
    for placeholder in ("", "   ", "-", "n/a", "Unbekannt", "onbekend"):
        assert vinted_adapter._size_text(placeholder) is None
    assert vinted_adapter._size_text("  38 / S  ") == "38 / S"


def test_listing_without_size_keeps_the_previous_display_text():
    listing = vinted_adapter._normalize_api(
        {"id": 12, "title": "Ohne Größe", "url": "/items/12", "status": "Gut"},
        "Test",
    )
    assert listing is not None
    assert listing["result_info"]["size"] is None
    assert listing["result_info"]["display_text"] == "Vinted · gebraucht · Einzelangebot"


def test_module_v2_exposes_size_additively_and_null_for_sources_without_one():
    with_size = listing_to_v2(
        {
            "id": "vinted:1",
            "title": "Kleid",
            "url": "https://www.vinted.de/items/1",
            "source": "vinted",
            "result_info": {"condition": "wie neu", "size": "M"},
        },
        "vinted",
    )
    without_size = listing_to_v2(
        {
            "id": "ebay:2",
            "title": "Konsole",
            "url": "https://www.ebay.de/itm/2",
            "source": "ebay",
            "result_info": {"condition": "gebraucht"},
        },
        "ebay",
    )
    assert with_size["size"] == "M"
    assert without_size["size"] is None
    # The additive field must not disturb the established v2 meanings.
    assert with_size["condition"] == "wie neu"
    assert without_size["offer"]["format"] == "fixed_price"
    assert without_size["offer"]["auction"] is False


def test_background_details_may_add_a_size_but_never_erase_the_catalog_one():
    assert "size" in _DETAIL_FIELDS
    original = {"result_info": {"condition": "wie neu", "size": "M"}}
    detail_without_size = {
        "result_info": {"condition": "wie neu"},
        "detail_enrichment": {"status": "ok", "fields": ["image", "price"]},
    }
    detail_with_size = {
        "result_info": {"condition": "wie neu", "size": "L"},
        "detail_enrichment": {"status": "ok", "fields": ["image", "size"]},
    }
    assert _merge_listing(original, detail_without_size)["result_info"]["size"] == "M"
    assert _merge_listing(original, detail_with_size)["result_info"]["size"] == "L"


def test_openapi_documents_the_additive_size_field_as_optional():
    schema = json.loads(read("docs/openapi-module-v2.json"))["components"]["schemas"]["Listing"]
    assert schema["properties"]["size"]["type"] == ["string", "null"]
    assert "size" not in schema.get("required", [])


def test_browser_offers_a_size_facet_that_separates_unknown_from_a_label():
    html = read("cloudflare/public/index.html")
    app_js = read("cloudflare/public/app.js")
    ui_js = read("cloudflare/public/ui-160.js")
    assert 'id="filter-size"' in html
    assert '<option value="none">Ohne Größenangabe</option>' in html
    assert "function refreshSizeOptions(items)" in app_js
    assert "const size=filterValue('filter-size');if(size==='none')" in app_js
    assert "{id: 'filter-size', defaultValue: 'all', label: 'Größe'}" in ui_js


def test_auctions_are_searched_by_default_and_hidden_by_the_result_filter():
    html = read("cloudflare/public/index.html")
    app_js = read("cloudflare/public/app.js")
    ui_js = read("cloudflare/public/ui-160.js")
    assert 'id="include-ebay-auctions" type="checkbox" checked' in html
    assert '<option value="no-auction" selected>Ohne Auktionen</option>' in html
    assert "if(format==='no-auction'){if(formatOf(x)==='auction')return false;}" in app_js
    assert "$('filter-format').value='no-auction';" in app_js
    assert "{id: 'filter-format', defaultValue: 'no-auction', label: 'Angebotsart'}" in ui_js


def test_module_contract_defaults_still_keep_auctions_opt_in_for_api_consumers():
    # The browser opts in explicitly; the contract default must stay unchanged
    # so that module-v1 and module-v2 consumers see no behaviour change.
    assert "include_auctions: bool = False" in read("src/generic_parser/module_api_v2.py")
    assert "include_ebay_auctions: bool = False" in read("src/generic_parser/module_api.py")
