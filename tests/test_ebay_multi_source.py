from __future__ import annotations

import asyncio

from generic_parser import search_service_v0450 as service
from generic_parser.module_api import (
    DebugTrace,
    ModuleDebugOptions,
    ModulePageRequest,
    ModuleSearchProfile,
    module_response_from_legacy,
)


def ka_result():
    return {
        "listings": [
            {
                "id": "ka-1",
                "title": "Evercade Interplay Collection 1",
                "url": "https://www.kleinanzeigen.de/s-anzeige/example/1",
                "price": 30,
                "match": {"decision": "accept"},
                "traffic_light": {"color": "green"},
            }
        ],
        "pagination": {
            "current_page": 0,
            "next_page": None,
            "complete": True,
            "source": "html-fallback",
            "unique_listings": 1,
        },
        "summary": {
            "fetched_listings": 1,
            "visible_listings": 1,
            "hidden_by_filter": 0,
            "reported_total": 1,
        },
        "traffic_light_summary": {"green": 1, "yellow": 0, "red": 0},
        "generated_urls": [],
        "worker": {},
    }


def test_auto_search_merges_all_three_sources(monkeypatch):
    async def fake_ka(payload, request):
        return ka_result()

    async def fake_vinted(query, page=0):
        return {
            "listings": [
                {
                    "id": "vinted:2",
                    "title": "Evercade Interplay Collection 1",
                    "url": "https://www.vinted.de/items/2-evercade",
                    "price": 25,
                    "source": "vinted",
                    "source_label": "Vinted",
                }
            ],
            "next_page": None,
            "status": "ok",
            "strategy": "service-binding",
            "http_status": 200,
            "url": "https://www.vinted.de/catalog?search_text=Evercade",
        }

    async def fake_ebay(query, **kwargs):
        assert kwargs["include_auctions"] is False
        return {
            "listings": [
                {
                    "id": "ebay:v1|3|0",
                    "title": "Evercade Interplay Collection 1",
                    "url": "https://www.ebay.de/itm/3",
                    "price": 24.99,
                    "item_price": 20,
                    "shipping_cost": 4.99,
                    "total_price": 24.99,
                    "source": "ebay",
                    "source_label": "eBay",
                    "transient": True,
                }
            ],
            "next_page": None,
            "status": "ok",
            "strategy": "official-browse-api",
            "marketplace": "EBAY_DE",
            "http_status": 200,
            "reported_total": 12,
            "include_auctions": False,
            "url": "https://www.ebay.de/sch/i.html?_nkw=Evercade",
        }

    monkeypatch.setattr(service.reference, "search_page", fake_ka)
    monkeypatch.setattr(service, "search_vinted", fake_vinted)
    monkeypatch.setattr(service, "search_ebay", fake_ebay)
    payload = service.SearchRequest.model_validate(
        {"mode": "live", "query": "Evercade", "source": "auto"}
    )
    result = asyncio.run(service.search_page(payload, None))
    assert len(result["listings"]) == 3
    assert {row["source"] for row in result["listings"]} == {
        "kleinanzeigen",
        "vinted",
        "ebay",
    }
    assert result["pagination"]["source"] == "multi-source"
    assert result["summary"]["reported_total"] is None
    assert result["source_status"]["ebay"] == {
        "enabled": True,
        "status": "ok",
        "strategy": "official-browse-api",
        "marketplace": "EBAY_DE",
        "visible": 1,
        "hidden": 0,
        "http_status": 200,
        "reason": None,
        "reported_total": 12,
        "include_auctions": False,
        "transient": True,
    }


def test_ebay_failure_does_not_remove_other_sources(monkeypatch):
    async def fake_ka(payload, request):
        return ka_result()

    async def fake_vinted(query, page=0):
        return {
            "listings": [],
            "next_page": None,
            "status": "degraded",
            "reason": "temporary",
        }

    async def failed_ebay(query, **kwargs):
        return {
            "listings": [],
            "next_page": None,
            "status": "degraded",
            "strategy": "official-browse-api",
            "marketplace": "EBAY_DE",
            "http_status": 429,
            "reason": "ebay_browse:API_BROWSE/2001",
            "transient": True,
        }

    monkeypatch.setattr(service.reference, "search_page", fake_ka)
    monkeypatch.setattr(service, "search_vinted", fake_vinted)
    monkeypatch.setattr(service, "search_ebay", failed_ebay)
    payload = service.SearchRequest.model_validate(
        {"mode": "live", "query": "Evercade", "source": "auto"}
    )
    result = asyncio.run(service.search_page(payload, None))
    assert [row["source"] for row in result["listings"]] == ["kleinanzeigen"]
    assert result["source_status"]["ebay"]["status"] == "degraded"
    assert result["source_status"]["ebay"]["http_status"] == 429


def test_module_contract_preserves_ebay_total_and_transient_marker():
    profile = ModuleSearchProfile(
        profile_id="evercade:test",
        display_name="Evercade Test",
        query="Evercade Test",
        include_ebay_auctions=False,
    )
    request = ModulePageRequest(profile=profile, page=0, source="ebay")
    result = {
        "listings": [
            {
                "id": "ebay:v1|123|0",
                "title": "Evercade Test",
                "url": "https://www.ebay.de/itm/123",
                "source": "ebay",
                "source_label": "eBay",
                "item_price": 20,
                "shipping_cost": 4.99,
                "total_price": 24.99,
                "price": 24.99,
                "currency": "EUR",
                "shipping_available": True,
                "buying_options": ["FIXED_PRICE"],
                "listing_format": "Sofort-Kaufen",
                "transient": True,
                "product_classification": {
                    "code": "main_product",
                    "label": "Hauptprodukt",
                    "ruleset": "product-classification-v1",
                },
            }
        ],
        "pagination": {
            "current_page": 0,
            "next_page": None,
            "complete": True,
            "source": "ebay",
            "unique_listings": 1,
        },
        "summary": {
            "fetched_listings": 1,
            "visible_listings": 1,
            "hidden_by_filter": 0,
            "reported_total": 1,
        },
    }
    response = module_response_from_legacy(
        result, request, DebugTrace(ModuleDebugOptions(), "test")
    )
    listing = response.listings[0]
    assert listing.source == "ebay"
    assert listing.total_price == 24.99
    assert listing.shipping_cost == 4.99
    assert listing.price == listing.total_price
    assert listing.buying_options == ["FIXED_PRICE"]
    assert listing.transient is True
    assert listing.product_classification["code"] == "main_product"
    assert listing.product_classification["ruleset"] == "product-classification-v1"
    assert profile.to_legacy_payload()["include_ebay_auctions"] is False
