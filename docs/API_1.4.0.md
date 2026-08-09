# GenericParser API 1.4.0

Version: `1.4.0`  
Build: `gp-140-20260809-1`  
Contract: `generic-parser-module-v1`

## Compatibility

The module contract and existing endpoint paths remain unchanged. Version 1.4.0 adds eBay as the third default source while retaining the proven Kleinanzeigen core and Vinted transport. Clients validate `generic-parser-module-v1`; an exact implementation build is not required.

`source: "auto"`, `"multi-source"` or `"all"` searches Kleinanzeigen, Vinted and eBay. A single source can still be selected with `"kleinanzeigen"`, `"vinted"` or `"ebay"`.

## Canonical request

```json
{
  "profile": {
    "profile_id": "evercade:collection",
    "display_name": "Evercade Collection",
    "query": "Evercade Collection",
    "max_price": 40,
    "market_value": 35,
    "include_ebay_auctions": false,
    "include_review": true,
    "include_rejected": true,
    "sort_by": "relevance"
  },
  "page": 0,
  "source": "auto"
}
```

`include_ebay_auctions` defaults to `false`. With the default, auction-only offers are excluded. Setting it to `true` permits fixed-price and auction results; each result still exposes its actual format.

The legacy flat search aliases accept the same additive `include_ebay_auctions` field.

## eBay listing fields

```json
{
  "id": "ebay:v1|123|0",
  "source": "ebay",
  "source_label": "eBay",
  "title": "Evercade Collection",
  "url": "https://www.ebay.de/itm/123",
  "item_price": 29.99,
  "shipping_cost": 4.99,
  "total_price": 34.98,
  "price": 34.98,
  "currency": "EUR",
  "shipping_available": true,
  "buying_options": ["FIXED_PRICE"],
  "listing_format": "Sofort-Kaufen",
  "auction": false,
  "bid_count": null,
  "item_end_date": "2026-08-12T20:00:00.000Z",
  "transient": true
}
```

Price semantics are deliberately conservative:

- `item_price` is the price reported for the item or current bid;
- `shipping_cost` is the lowest known shipping cost;
- `total_price` is `item_price + shipping_cost` only when shipping is known, or the item price for pickup-only offers;
- `price`, the established matching and traffic-light input, equals `total_price` only when that total is trustworthy;
- if shipping is unknown, `shipping_cost`, `total_price` and `price` are `null` while `item_price` remains visible.

This prevents an item with undisclosed shipping from being scored as an artificially cheap deal.

## Source status

Every multi-source response includes an `ebay` entry in `source_status` and `summary.sources`:

```json
{
  "enabled": true,
  "status": "ok",
  "strategy": "official-browse-api",
  "marketplace": "EBAY_DE",
  "visible": 25,
  "include_auctions": false,
  "transient": true
}
```

OAuth or Browse failures produce `status: "degraded"` with a sanitized `reason`. They do not fail successful Kleinanzeigen or Vinted results.

## Capabilities

`GET /api/module/v1/capabilities` advertises all three default sources and the eBay contract: official Browse API, `EBAY_DE`, fixed-price default, optional auctions, total-including-known-shipping semantics and no persistence.

## Data lifetime

Application OAuth credentials are supplied as Cloudflare secrets. Access tokens are cached only in Worker isolate memory until shortly before expiry. eBay listings are returned to the caller but excluded from the bundled browser's IndexedDB serialization. GenericParser does not provide server-side eBay listing persistence.

## Unchanged endpoints

Health, version, diagnostics, profile validation, canonical and legacy search, network-free self-test, and both Vinted enrichment endpoints retain their 1.3.4 paths. Vinted background enrichment remains limited to three detail pages per request and does not block catalog pagination.
