# GenericParser API 1.3.4

Version: `1.3.4`  
Build: `gp-134-20260809-1`  
Contract: `generic-parser-module-v1`

## Compatibility

The API and search runtime are unchanged from 1.3.3. Evercade, SNES PAL and generic clients continue to use the same module-v1 profiles, search aliases and Vinted detail-enrichment endpoints. Exact implementation-version matching is not required; consumers validate the API contract.

1.3.4 changes browser presentation only:

- no request or response fields are added, removed or renamed;
- matching, traffic-light scoring, extraction and pagination are unchanged;
- the client-side Vinted background queue keeps the three-item limit;
- card descriptions remain cleaned and clamped only at render time;
- the denser grid and side-by-side card media do not alter returned listing data.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Runtime identity and readiness |
| GET | `/version`, `/api/version` | Release and contract identity |
| GET | `/diagnostics` | Routing, CORS and source capabilities |
| GET | `/api/module/v1/capabilities` | Module-v1 sources and enrichment limits |
| POST | `/api/module/v1/profile/validate` | Validate a module profile |
| POST | `/api/module/v1/search` | Canonical module-v1 page search |
| POST | `/api/module/search` | Canonical or Evercade compatibility packet |
| POST | `/api/search`, `/search` | Legacy flat page search |
| POST | `/api/vinted/enrich` | Deferred Vinted details for flat/browser clients |
| POST | `/api/module/v1/vinted/enrich` | Deferred Vinted details for module-v1 clients |
| GET | `/api/module/v1/self-test?enabled=true` | Explicit network-free contract test |

All search aliases return catalog results page by page. At most three Vinted detail pages are opened inside a catalog request; remaining incomplete Vinted listings can be sent to the deferred enrichment endpoint.

## Canonical module search

### Request

```json
{
  "profile": {
    "profile_id": "evercade:collection",
    "display_name": "Evercade Collection",
    "query": "Evercade Collection",
    "required_terms": ["evercade"],
    "excluded_terms": ["defekt"],
    "max_price": 40,
    "market_value": 35,
    "accept_bundles": false,
    "accept_incomplete": false,
    "include_review": true,
    "include_rejected": true,
    "sort_by": "relevance"
  },
  "page": 0,
  "source": "auto"
}
```

Empty optional profile fields are ignored. `source: "auto"` enables the configured Kleinanzeigen and Vinted sources.

### Response shape

```json
{
  "contract": "generic-parser-module-v1",
  "listings": [
    {
      "id": "vinted:123",
      "title": "Evercade Collection",
      "url": "https://www.vinted.de/items/123-evercade-collection",
      "source": "vinted",
      "source_label": "Vinted",
      "image_url": "https://...",
      "price": 35,
      "description": "Complete source description",
      "detail_enrichment": {
        "status": "ok",
        "fields": ["image", "price", "description", "condition"]
      },
      "match": {"decision": "accept", "score": 100},
      "traffic_light": {"color": "green"}
    }
  ],
  "pagination": {
    "current_page": 0,
    "next_page": 1,
    "complete": false,
    "source": "multi"
  }
}
```

The full `description` remains available to API clients. The bundled browser UI removes hashtag-only lines and trailing runs of three or more hashtag tokens from visible card text, then clamps the remainder to four lines until `Mehr anzeigen` is selected. This does not mutate the stored or returned listing.

## Deferred Vinted enrichment

Both enrichment paths execute the same bounded operation:

- one request accepts 1 to 3 already returned Vinted listings;
- only canonical `https://www.vinted.de/items/...` URLs whose ID matches the listing ID are accepted;
- up to three detail pages run in parallel within a batch;
- clients serialize batches so only one batch is active per queue;
- errors are isolated from catalog pagination;
- updated price and condition trigger matching and traffic-light rescoring.

### Flat request

```json
{
  "search": {
    "mode": "live",
    "query": "Evercade",
    "max_price": 40,
    "page": 0,
    "source": "vinted"
  },
  "listings": [
    {
      "id": "vinted:123",
      "title": "Evercade Collection",
      "url": "https://www.vinted.de/items/123-evercade-collection",
      "source": "vinted",
      "detail_enrichment": {"status": "skipped_budget", "fields": []}
    }
  ]
}
```

### Module-v1 request

```json
{
  "profile": {
    "profile_id": "snes:super-metroid",
    "display_name": "Super Metroid",
    "query": "Super Metroid",
    "max_price": 70
  },
  "page": 0,
  "listings": [
    {
      "id": "vinted:123",
      "title": "Super Metroid PAL",
      "url": "https://www.vinted.de/items/123-super-metroid-pal",
      "source": "vinted"
    }
  ]
}
```

### Response

```json
{
  "status": "ok",
  "contract": "generic-parser-module-v1",
  "mode": "background-batch",
  "strategy": "service-binding-deferred-detail",
  "detail_batch_limit": 3,
  "requested": 1,
  "complete": 1,
  "partial": 0,
  "failed": 0,
  "listings": [
    {
      "id": "vinted:123",
      "image_url": "https://...",
      "price": 35,
      "description": "...",
      "detail_enrichment": {
        "status": "ok",
        "fields": ["image", "price", "description", "condition"],
        "mode": "background-batch"
      },
      "match": {"decision": "accept", "score": 100},
      "traffic_light": {"color": "green"}
    }
  ]
}
```

HTTP `422` is returned for malformed input, more than three listings, a non-Vinted URL or an ID/URL mismatch. A Browser Run or binding failure is represented per listing as `detail_enrichment.status = background_error`; the main result remains available.

## Browser queue behavior

The bundled UI renders each catalog page immediately, queues incomplete Vinted listings, drains one three-item batch at a time, merges returned fields by listing ID and re-renders the existing cards. Starting a new search aborts the previous queue; stopping a search cancels pending client-side batches.

## Limitations

- Detail data depends on Vinted's publicly rendered item page and may be absent or access-limited.
- Text-only catalog entries without a canonical item URL cannot be enriched.
- Background completion is client-driven; closing or reloading the page stops the in-memory queue.
- The feature does not bypass authentication, CAPTCHA, rate limits or other access controls.
- UI-only card sizing and description cleanup do not alter API payloads, matching or scoring.
