# GenericParser API 1.6.0

Version: `1.6.0`

Build: `gp-160-20260810-1`

Preferred contract: `generic-parser-module-v2`

Compatible contract: `generic-parser-module-v1`

## Scope

Module API v2 is a project-independent interface for browser and embedded
clients. It accepts plain search definitions and returns normalized listings
from Kleinanzeigen, Vinted and eBay. It intentionally contains no cartridge
catalog, collection, market-value or deal model.

The existing module-v1 endpoints and payloads remain available without a
breaking change. `/health`, `/version` and response headers publish both
supported contracts and identify v2 as preferred.

## Endpoints

- `GET /api/module/v2/capabilities`
- `POST /api/module/v2/validate`
- `POST /api/module/v2/search`
- `POST /api/module/v2/batch`

The machine-readable specification is
[`openapi-module-v2.json`](openapi-module-v2.json).

## Packet model

Each search or batch request processes exactly one source page. A partial
response contains an opaque, HMAC-SHA256-signed `continuation_token`. Send the
unchanged definition and token again to process the next packet. The token:

- is bound to batch ID, client identity and all search definitions;
- expires after two hours;
- contains cursors and counters, but no listing results;
- returns `409` when invalid or used with changed definitions;
- returns `410` when expired.

Persistent server-side jobs are not part of 1.6.0. Clients may save the opaque
token and resume while it remains valid.

## Single-search example

```json
{
  "contract": "generic-parser-module-v2",
  "batch_id": "web-20260810-1",
  "client": {
    "project_id": "my-browser-client",
    "project_version": "2.3.0"
  },
  "search": {
    "search_id": "model-train",
    "query": "Märklin H0/AC",
    "sources": ["kleinanzeigen", "vinted", "ebay"],
    "criteria": {
      "required_terms": ["Märklin", "H0/AC"],
      "excluded_terms": ["defekt", "nur OVP"]
    },
    "filters": {
      "max_price": 90,
      "accept_bundles": false,
      "accept_incomplete": false,
      "include_auctions": false,
      "include_review": true,
      "include_rejected": true
    },
    "location": {},
    "sort_by": "relevance"
  },
  "continuation_token": null,
  "debug": {"enabled": false}
}
```

Term fields accept either an array or a comma-separated string. Whitespace,
empty entries and case-insensitive duplicates are normalized. Umlauts, `/`
and other search characters remain intact.

## Listing semantics

Every returned listing has a stable packet identity `listing_key` in the form
`source:source_id`, plus source, URL, title, optional image and description,
price components, delivery/location facts, offer format, condition,
classification and timestamps.

`pricing.total_known` distinguishes a trustworthy item-plus-shipping total
from an open shipping total. Ordinary eBay results remain transient. Seller
and account identifiers are not part of the v2 listing.

## Source status and HTTP behavior

Each packet reports one normalized source status: `ok`, `empty`, `partial`,
`blocked`, `rate_limited`, `timeout`, `unavailable` or `disabled`. It also
reports retryability, an optional retry interval, source HTTP status and a
stable error code.

- `200`: packet processed, including partial/degraded results;
- `409`: invalid or conflicting continuation;
- `410`: expired continuation;
- `422`: invalid request definition;
- `502`: the processed packet failed and no source result was available.

## Web client

The 1.6.0 browser UI uses `/api/module/v2/search`. It keeps search criteria
separate from result filters, provides comma/Enter term chips, platform
selection, per-source progress, active filter chips, recent searches and
mobile filter disclosure. Visible statuses are `Passend`, `Prüfen` and
`Unpassend`; the underlying product-classification ruleset is unchanged.

## Data handling

No server-side result history or search-job store was added. Browser search
progress remains local. Explicit favorites remain browser-local and omit
description, seller and account data. The signed eBay Marketplace Account
Deletion endpoint and its no-user-data behavior are unchanged.
