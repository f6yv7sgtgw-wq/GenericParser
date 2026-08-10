from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser import vinted_enrichment
from generic_parser.cloudflare_v0452 import app
from generic_parser.release_identity import BUILD_ID, VERSION
from generic_parser.search_service_v0450 import SearchRequest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_and_rollback_are_consistent():
    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert VERSION == "1.5.0"
    assert BUILD_ID == "gp-150-20260810-1"
    assert metadata["version"] == public["version"] == VERSION
    assert metadata["build_id"] == public["build_id"] == BUILD_ID
    assert metadata["status"] in {"release-candidate", "stable"}
    assert metadata["rollback_plan"] == {
        "last_stable_baseline": "1.4.0",
        "build_id": "gp-140-20260809-1",
    }


def test_capabilities_publish_classification_filters_favorites_and_deletion_endpoint():
    response = TestClient(app).get("/api/module/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contract"] == "generic-parser-module-v1"
    assert payload["classification"]["ruleset"] == "product-classification-v1"
    assert payload["classification"]["traffic_order"] == ["green", "yellow", "orange", "red"]
    assert set(payload["classification"]["classes"]) == {
        "main_product",
        "accessory_part",
        "bundle",
        "wanted",
        "rental",
        "service",
        "related_merchandise",
        "unknown",
    }
    assert payload["ui"] == {
        "result_filters": True,
        "listing_description_visible": False,
        "favorites_page": "/favorites.html",
    }
    assert payload["ebay"]["favorite_fields_contain_seller_data"] is False
    assert payload["ebay"]["notification_signature_verification"] == "ecdsa-public-key-api"


def test_browser_has_all_requested_filters_and_red_is_hidden_by_default():
    html = read("cloudflare/public/index.html")
    for identifier in (
        "filter-traffic",
        "filter-source",
        "filter-product-class",
        "filter-condition",
        "filter-price-min",
        "filter-price-max",
        "filter-shipping",
        "filter-scope",
        "filter-format",
    ):
        assert f'id="{identifier}"' in html
    assert '<option value="without-red" selected>' in html
    assert "Grüne Treffer bleiben" in html
    assert "ui-150.css" in html


def test_green_group_is_fixed_before_user_sort_and_description_is_not_rendered():
    app_js = read("cloudflare/public/app.js")
    assert "const rank={green:0,yellow:1,orange:2,red:3}" in app_js
    assert "||within(x,y)" in app_js
    card = app_js[app_js.index("function card(x)"):app_js.index("function syncDescriptionControls")]
    assert "descriptionMarkup(x)" not in card
    assert "favorite-toggle" in card
    assert "product-class-badge" in card


def test_explicit_favorites_are_isolated_and_omit_description_and_seller_data():
    html = read("cloudflare/public/favorites.html")
    store = read("cloudflare/public/favorites-store-150.js")
    service_worker = read("cloudflare/public/service-worker.js")
    assert 'id="favorites-results"' in html
    assert "nur in diesem Browser gespeichert" in html
    assert "generic-parser-favorites-v1" in store
    snapshot = store[store.index("function snapshot(listing)"):store.index("function all()")]
    assert "description:" not in snapshot
    assert "seller:" not in snapshot
    assert "contains_seller_data: false" in snapshot
    assert '"./favorites.html"' in service_worker
    assert '"./favorites-store-150.js"' in service_worker
    assert '"./favorites-150.js"' in service_worker


def test_log_header_logo_is_removed_on_both_pages():
    search_header = read("cloudflare/public/index.html").split("</header>", 1)[0]
    log_header = read("cloudflare/public/eventlog.html").split("</header>", 1)[0]
    assert 'class="brand-mark"' not in search_header
    assert 'class="brand-mark"' not in log_header


def test_ebay_adapter_discards_seller_identifiers_before_results_reach_browser():
    adapter = read("src/generic_parser/ebay_adapter.py")
    normalized = adapter[adapter.index("def _normalize_item"):adapter.index("def _safe_error_reason")]
    assert '"seller"' not in normalized
    assert "Seller/account identifiers are deliberately discarded" in normalized


def test_signed_ebay_deletion_component_and_deployment_gate_are_present():
    worker = read("pocs/ebay-notifications/src/index.js")
    workflow = read(".github/workflows/cloudflare-deploy.yml")
    config = json.loads(read("pocs/ebay-notifications/wrangler.jsonc"))
    endpoint = "https://genericparser-ebay-notifications.f6yv7sgtgw.workers.dev/marketplace-account-deletion"
    assert config["vars"]["EBAY_DELETION_ENDPOINT_URL"] == endpoint
    assert "challengeResponse" in worker
    assert "crypto.subtle.verify" in worker
    assert "PUBLIC_KEY_URL" in worker
    assert "x-ebay-signature" in worker
    assert "user_data_stored: false" in worker
    assert "EBAY_DELETION_VERIFICATION_TOKEN" in workflow
    assert "[A-Za-z0-9_-]{32,80}" in workflow
    assert "Verify eBay endpoint health and challenge contract" in workflow
    assert "ebay_has_no_seller_data" in workflow
    assert "all_classified" in workflow


def test_vinted_background_enrichment_preserves_product_classification(monkeypatch):
    async def fake_details(listings):
        return {
            "status": "ok",
            "strategy": "test",
            "listings": [
                {
                    **listings[0],
                    "price": 15,
                    "description": "Detail text must not change the product type.",
                    "detail_enrichment": {
                        "status": "ok",
                        "fields": ["price", "description"],
                    },
                }
            ],
        }

    monkeypatch.setattr(vinted_enrichment, "enrich_vinted_details", fake_details)
    payload = SearchRequest.model_validate(
        {"mode": "live", "query": "Super Mario Kart 8", "source": "vinted"}
    )
    original = {
        "id": "vinted:123",
        "title": "CARRERA Pull & Speed Super Mario Kart Mach 8",
        "url": "https://www.vinted.de/items/123-carrera",
        "source": "vinted",
        "result_info": {
            "condition": "gebraucht",
            "scope": "Einzelangebot",
            "offer_type": "Produkt",
        },
    }

    import asyncio

    result = asyncio.run(vinted_enrichment.enrich_vinted_batch([original], payload))
    listing = result["listings"][0]
    assert listing["product_classification"]["code"] == "related_merchandise"
    assert listing["result_info"]["product_class"] == "related_merchandise"
    assert listing["traffic_light"]["color"] == "red"
    assert listing["match"]["decision"] == "reject"


def test_release_documentation_covers_data_handling_and_known_junk_examples():
    api = read("docs/API_1.5.0.md")
    release = read("docs/releases/1.5.0.md")
    roadmap = read("ROADMAP.md")
    assert "product-classification-v1" in api
    assert "seller usernames" in api
    assert "Level 8 Super Mario Kartenspiel" in release
    assert "Jakks Super Mario Kart" in release
    assert "CARRERA Pull & Speed" in release
    assert "1.5.0 release candidate" in roadmap
