# GenericParser API 1.3.2

Version: `1.3.2`  
Build: `gp-132-20260809-1`  
Contract: `generic-parser-module-v1`

## Compatibility

The existing search contract is unchanged. Evercade, SNES PAL and generic clients continue to use the same module-v1 profiles and search endpoints. Exact implementation-version matching is not required; consumers must validate the API contract.

Additive changes in 1.3.2:

- `ModuleListing` now explicitly preserves `description`, `source_label` and `detail_enrichment`.
- Capabilities report both `kleinanzeigen` and `vinted`.
- A bounded detail-enrichment endpoint is available for browser and module clients.

## Existing endpoints

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
| GET | `/api/module/v1/self-test?enabled=true` | Explicit network-free contract test |

All search aliases still return catalog results page by page. The 1.3.1 critical-path limit remains: at most three Vinted detail pages are opened within a catalog request.

## Deferred Vinted enrichment

| Method | Path | Audience |
|---|---|---|
| POST | `/api/vinted/enrich` | GenericParser browser UI / flat search clients |
| POST | `/api/module/v1/vinted/enrich` | Evercade, SNES PAL and other module-v1 clients |

Both paths execute the same bounded operation:

- one request accepts 1 to 3 already returned Vinted listings;
- only canonical `https://www.vinted.de/items/...` URLs whose ID matches the listing ID are accepted;
- the three detail pages run in parallel;
- clients serialize batches, so only one three-item batch is active per client queue;
- failure is isolated from catalog pagination;
- updated price and condition trigger matching/traffic-light rescoring.

### Flat search request

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
    "profile_id": "evercade:collection",
    "display_name": "Evercade Collection",
    "query": "Evercade Collection",
    "max_price": 40
  },
  "page": 0,
  "listings": [
    {
      "id": "vinted:123",
      "title": "Evercade Collection",
      "url": "https://www.vinted.de/items/123-evercade-collection",
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

HTTP `422` is returned for malformed input, more than three listings, a non-Vinted URL or an ID/URL mismatch. A Browser Run or binding failure is represented per listing as `detail_enrichment.status = background_error`; the endpoint remains fail-open and the main search result is preserved.

## Browser behavior

The bundled UI automatically queues incomplete Vinted listings. It immediately renders the catalog page, drains a serial queue in three-item batches, merges returned fields by listing ID and re-renders the existing cards. The status card and Eventlog expose queued, processed, complete, partial and failed counts.

Stopping a search cancels pending client-side detail batches. Starting a new search aborts the old queue so results cannot leak between sessions.

## Limitations

- Detail data depends on Vinted's publicly rendered item page and may be absent or access-limited.
- Text-only catalog entries without a canonical item URL cannot be enriched.
- Background completion is client-driven; closing or reloading the page stops the in-memory queue.
- The feature does not bypass authentication, CAPTCHA, rate limits or other access controls.
- The main search retains the 1.3.1 limit of three inline detail pages and therefore keeps its proven timeout protection.
