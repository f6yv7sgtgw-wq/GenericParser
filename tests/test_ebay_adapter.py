from __future__ import annotations

import asyncio

import httpx

import generic_parser.ebay_adapter as ebay


def ebay_item(*, shipping=True, buying_options=None):
    item = {
        "itemId": "v1|123456789|0",
        "legacyItemId": "123456789",
        "title": "Evercade Interplay Collection 1",
        "itemWebUrl": "https://www.ebay.de/itm/123456789",
        "price": {"value": "20.00", "currency": "EUR"},
        "buyingOptions": buying_options or ["FIXED_PRICE"],
        "condition": "Sehr gut",
        "image": {"imageUrl": "https://i.ebayimg.com/images/example.jpg"},
        "itemLocation": {"postalCode": "10115", "city": "Berlin"},
        "itemOriginDate": "2026-08-09T19:00:00.000Z",
        "shortDescription": "Komplett mit Hülle.",
        "seller": {
            "username": "seller",
            "feedbackPercentage": "99.8",
            "feedbackScore": 321,
        },
    }
    if shipping:
        item["shippingOptions"] = [
            {"shippingCost": {"value": "4.99", "currency": "EUR"}}
        ]
    return item


def test_fixed_price_item_uses_item_plus_known_shipping_total():
    listing = ebay._normalize_item(
        ebay_item(), "Evercade", include_auctions=False
    )
    assert listing is not None
    assert listing["id"] == "ebay:v1|123456789|0"
    assert listing["source"] == "ebay"
    assert listing["source_label"] == "eBay"
    assert listing["item_price"] == 20.0
    assert listing["shipping_cost"] == 4.99
    assert listing["total_price"] == 24.99
    assert listing["price"] == 24.99
    assert listing["currency"] == "EUR"
    assert listing["shipping_available"] is True
    assert listing["listing_format"] == "Sofort-Kaufen"
    assert listing["transient"] is True


def test_unknown_shipping_never_pretends_item_price_is_total():
    listing = ebay._normalize_item(
        ebay_item(shipping=False), "Evercade", include_auctions=False
    )
    assert listing is not None
    assert listing["item_price"] == 20.0
    assert listing["shipping_cost"] is None
    assert listing["total_price"] is None
    assert listing["price"] is None
    assert listing["price_raw"] == "20 € + Versand offen"


def test_auction_only_listing_is_default_off_and_explicitly_available():
    raw = ebay_item(buying_options=["AUCTION"])
    raw["currentBidPrice"] = {"value": "12.50", "currency": "EUR"}
    assert ebay._normalize_item(raw, "Evercade", include_auctions=False) is None
    listing = ebay._normalize_item(raw, "Evercade", include_auctions=True)
    assert listing is not None
    assert listing["auction"] is True
    assert listing["listing_format"] == "Auktion"
    assert listing["item_price"] == 12.5
    assert listing["total_price"] == 17.49


def test_production_client_reuses_token_and_builds_german_browse_requests():
    calls = {"token": 0, "browse": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(ebay.EBAY_TOKEN_URL):
            calls["token"] += 1
            assert request.method == "POST"
            assert request.headers["authorization"].startswith("Basic ")
            return httpx.Response(
                200,
                json={
                    "access_token": "test-application-token",
                    "expires_in": 7200,
                    "token_type": "Application Access Token",
                },
            )
        calls["browse"] += 1
        assert str(request.url).startswith(ebay.EBAY_SEARCH_URL)
        assert request.headers["x-ebay-c-marketplace-id"] == "EBAY_DE"
        assert request.headers["x-ebay-c-enduserctx"] == (
            "contextualLocation=country=DE,zip=10115"
        )
        assert request.url.params["limit"] == "25"
        assert request.url.params["fieldgroups"] == "EXTENDED"
        assert "deliveryCountry:DE" in request.url.params["filter"]
        if calls["browse"] <= 2:
            assert "buyingOptions" not in request.url.params["filter"]
        else:
            assert "buyingOptions:{FIXED_PRICE|AUCTION}" in request.url.params["filter"]
        offset = int(request.url.params["offset"])
        return httpx.Response(
            200,
            json={
                "total": 30,
                "next": "https://api.ebay.com/next" if offset == 0 else None,
                "itemSummaries": [ebay_item()],
            },
        )

    async def scenario():
        ebay._reset_token_cache_for_tests()
        token = ebay.set_ebay_credentials("production-client-id", "production-secret")
        try:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:
                first = await ebay.search_ebay(
                    "Evercade",
                    page=0,
                    postal_code="10115",
                    client=client,
                )
                second = await ebay.search_ebay(
                    "Evercade", page=1, postal_code="10115", client=client
                )
                auction_opt_in = await ebay.search_ebay(
                    "Evercade",
                    page=0,
                    postal_code="10115",
                    include_auctions=True,
                    client=client,
                )
        finally:
            ebay.reset_ebay_credentials(token)
            ebay._reset_token_cache_for_tests()
        return first, second, auction_opt_in

    first, second, auction_opt_in = asyncio.run(scenario())
    assert calls == {"token": 1, "browse": 3}
    assert first["status"] == "ok"
    assert first["marketplace"] == "EBAY_DE"
    assert first["next_page"] == 1
    assert first["reported_total"] == 30
    assert first["listings"][0]["total_price"] == 24.99
    assert second["next_page"] is None
    assert auction_opt_in["include_auctions"] is True


def test_missing_credentials_is_fail_open_without_network_request():
    async def scenario():
        ebay._reset_token_cache_for_tests()
        token = ebay.set_ebay_credentials(None, None)
        try:
            return await ebay.search_ebay("Evercade")
        finally:
            ebay.reset_ebay_credentials(token)

    result = asyncio.run(scenario())
    assert result["status"] == "degraded"
    assert result["reason"] == "ebay_credentials_unavailable"
    assert result["listings"] == []
    assert result["transient"] is True
