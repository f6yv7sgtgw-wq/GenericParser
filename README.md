# GenericParser

Stable reusable Kleinanzeigen parser module and browser UI for **Evercade**, **SNES PAL Sammlung** and future projects.

## Current release

- **Version:** `1.3.4`
- **Build:** `gp-134-20260809-1`
- **Status:** Stable; production, multi-source, deferred-detail and GUI gates passed
- **Worker profile:** Cloudflare Workers Paid
- **Module contract:** `generic-parser-module-v1`
- **Search runtime:** `0.45.0`
- **Functional search core:** `0.44.4`
- **Operational reference:** `0.44.6.5`

GenericParser 1.3.4 is a focused browser-interface refinement on top of the production-proven 1.3.3 release. Results use a dense multi-column grid, each card keeps its thumbnail and text side by side, and the decorative SNES-style mark is removed from the search-page header. Search, matching, scoring, pagination, four-line Vinted descriptions and background enrichment are unchanged.

## Architecture

```text
Evercade / SNES / other client
        ↓
generic-parser-module-v1
        ↓
GenericParser Worker
        ↓
Kleinanzeigen runtime + private Vinted Service Binding
        ↓
Immediate catalog response + deferred Vinted detail batches
```

## Public endpoints

- `GET /health`
- `GET /version`
- `GET /diagnostics`
- `GET /api/module/v1/capabilities`
- `POST /api/module/v1/profile/validate`
- `POST /api/module/v1/search`
- `POST /api/module/search`
- `POST /api/search`
- `POST /search`
- `POST /api/vinted/enrich`
- `POST /api/module/v1/vinted/enrich`
- `GET /api/module/v1/self-test?enabled=true`

The two enrichment paths are additive support endpoints. They accept at most three already returned Vinted listings, validate canonical item URLs, load those three detail pages in parallel and return updated listings with matching and traffic-light scoring recalculated. The bundled browser uses them automatically; module-v1 clients may use the canonical module path.

## Paid Worker profile

Free-Worker protection waits are disabled:

- new-search cooldown: `0 ms`
- normal packet delay: `0 ms`
- retry waits: `0 ms`
- auto-resume quiet period: effectively immediate
- recovery health interval: effectively immediate

The proven seven-result Kleinanzeigen work-packet structure remains unchanged. Vinted background work uses serial three-item batches with no artificial delay and never blocks the primary search request.

## Module contract

`generic-parser-module-v1` remains the stable integration boundary. Clients should rely on the contract instead of pinning an exact implementation build.

Example module request:

```json
{
  "profile": {
    "profile_id": "evercade:interplay-1",
    "display_name": "Evercade · Interplay Collection 1",
    "query": "Evercade Interplay Collection 1",
    "brands": ["Evercade", "Blaze"],
    "max_price": 35,
    "market_value": 30,
    "accept_bundles": false,
    "accept_incomplete": false
  },
  "page": 0,
  "source": "auto",
  "debug": {"enabled": false}
}
```

Empty optional profile fields are ignored before the reference search core is called.

## Project adapters

```python
from generic_parser import evercade_profile, snes_pal_profile

profile = evercade_profile("Interplay Collection 1", market_value=30, max_price=35)
snes = snes_pal_profile("Super Metroid", market_value=70)
```

## Diagnostics

Debug logging and network-free module self-tests remain opt-in and are disabled by default. Production diagnostics cover version/build identity, API contract, routing, CORS/preflight and endpoint availability.

## Vinted detail behavior

- Inline critical path: maximum 3 detail pages per Vinted catalog page.
- Deferred path: maximum 3 detail pages per request, parallel within the batch.
- Client queue: one deferred batch at a time.
- Detail timeout: 6 seconds per Browser Run navigation.
- Merge: image, price, description and condition update the existing card.
- Scoring: updated price and condition are re-evaluated.
- Failure model: fail-open; catalog results remain available.
- Access policy: no login, CAPTCHA, rate-limit or access-control bypass.

## Browser interface

- Shared dark visual language with the Evercade and SNES projects.
- `Log & Diagnose` is available directly in the top header.
- The former visible technical-details expander is removed; diagnostics continue to be recorded in the dedicated log page.
- Search results use a dense responsive grid: three or more cards fit across normal desktop widths and four to five fit on wider displays.
- Every result card keeps a small square thumbnail and its text side by side, including on phone layouts.
- The decorative four-dot project mark is removed from the search-page header.
- Result cards retain source, traffic-light, condition and action regions without horizontal scrolling.
- Descriptions are clamped to four lines by default and remain expandable.
- Hashtag-only lines and trailing hashtag blocks are omitted from card text.

## Release quality gate

A stable release requires:

1. syntax and compile checks;
2. search-core regression tests;
3. module-contract checks;
4. Cloudflare deployment;
5. live `/health`, `/version`, `/diagnostics` validation;
6. browser CORS/preflight validation;
7. live Evercade module packet;
8. live legacy `/api/search` packet;
9. live deferred Vinted detail batch without catalog-path regression;
10. exact-source ZIP artifact.

## Versioning

From 1.0 onward GenericParser uses semantic versioning. Search-core changes are explicit functional changes; infrastructure changes must not silently change matching, ranking, extraction or pagination. 1.3.4 changes only browser presentation and keeps the 1.3.3 source and transport behavior intact.

Further documentation: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md), [`VERSION.json`](VERSION.json), [`docs/API_1.3.4.md`](docs/API_1.3.4.md), [`docs/RELEASE_INDEX.md`](docs/RELEASE_INDEX.md) and [`docs/releases/1.3.4.md`](docs/releases/1.3.4.md).
