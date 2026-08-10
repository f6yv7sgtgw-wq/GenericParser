# GenericParser

Reusable multi-source marketplace parser and browser UI for **Evercade**, **SNES PAL Sammlung** and future projects.

## Current release

- **Version:** `1.5.1`
- **Build:** `gp-151-20260810-1`
- **Status:** Release candidate; local regression, stop-status and responsive-filter gates passed
- **Worker profile:** Cloudflare Workers Paid
- **Module contract:** `generic-parser-module-v1`
- **Search runtime:** `0.45.0`
- **Functional search core:** `0.44.4`
- **Operational reference:** `0.44.6.5`

GenericParser 1.5.1 corrects the contradictory completion message after a manual stop and presents the result filters in balanced, responsive rows. A stopped run is now explicitly shown and logged as incomplete, saved and resumable. The proven classification, three-source search, fixed-price eBay default, explicit favorites and signed Marketplace Account Deletion endpoint remain unchanged from 1.5.0.

## Architecture

```text
Evercade / SNES / other client
        ↓
generic-parser-module-v1
        ↓
GenericParser Worker
        ↓
Kleinanzeigen runtime + private Vinted Service Binding + eBay Browse API
        ↓
Classified catalog response + deferred Vinted details + explicit browser favorites
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

eBay Marketplace Account Deletion endpoint:

- `GET/POST https://genericparser-ebay-notifications.f6yv7sgtgw.workers.dev/marketplace-account-deletion`

The two enrichment paths remain Vinted-only additive support endpoints. They accept at most three already returned Vinted listings, validate canonical item URLs, load those three detail pages in parallel and return updated listings with matching and traffic-light scoring recalculated. The bundled browser uses them automatically; module-v1 clients may use the canonical module path.

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
    "accept_incomplete": false,
    "include_ebay_auctions": false
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

## eBay behavior

- Transport: official eBay Production Browse API.
- Marketplace and delivery country: `EBAY_DE` / `DE`.
- Result page size: 25.
- Fixed-price offers are enabled by default; auction-only offers require `include_ebay_auctions: true`.
- `item_price` always remains distinct from `shipping_cost` and `total_price`.
- Matching uses `price = total_price` only when shipping is known or the offer is pickup-only.
- Unknown shipping is shown as open and is never treated as free.
- OAuth tokens live only in Worker memory until expiry.
- eBay search results are not stored server-side and remain excluded from browser search-state IndexedDB persistence.
- Only a listing explicitly marked with the star is stored in the current browser. The favorite snapshot omits description, seller name, seller ID and all account data.
- Signed eBay deletion notifications are verified with eBay's public-key API; the endpoint stores no notification user data.
- OAuth/Browse failures degrade only eBay; other source results remain available.

## Browser interface

- Shared dark visual language with the Evercade and SNES projects.
- `Log & Diagnose` is available directly in the top header.
- The former visible technical-details expander is removed; diagnostics continue to be recorded in the dedicated log page.
- Search results use a dense responsive grid: three or more cards fit across normal desktop widths and four to five fit on wider displays.
- Every result card keeps a small square thumbnail and its text side by side, including on phone layouts.
- The decorative four-dot project mark is removed from the search-page header.
- Result cards retain source, traffic-light, condition and action regions without horizontal scrolling.
- Listing descriptions are no longer displayed, making every card shorter.
- Green results always precede yellow, orange and red results; the chosen sort applies only within each color group.
- Filters cover traffic light, source, product class, condition, total price, shipping, scope and offer format. Red results are hidden by default but remain selectable.
- Manual stops are labelled as paused and resumable, never as fully completed.
- Result filters use two balanced desktop rows and responsive three-, two- and one-column layouts at narrower widths.
- The star in the upper-right corner saves an explicit favorite; `/favorites.html` lists and filters saved offers.
- The decorative project mark is removed from both search and log headers.

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
9. live three-source packet with official eBay transport and fixed-price default;
10. eBay known-shipping total-price validation;
11. live deferred Vinted detail batch without catalog-path regression;
12. classification regression against known game/merchandise examples;
13. eBay deletion challenge and signed-notification verification;
14. exact-source ZIP artifact.

## Versioning

From 1.0 onward GenericParser uses semantic versioning. Search-core changes are explicit functional changes; infrastructure changes must not silently change extraction or pagination. 1.5.1 is a presentation-and-status patch on the unchanged 1.5.0 search behavior.

Further documentation: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md), [`VERSION.json`](VERSION.json), [`docs/API_1.5.1.md`](docs/API_1.5.1.md), [`docs/RELEASE_INDEX.md`](docs/RELEASE_INDEX.md) and [`docs/releases/1.5.1.md`](docs/releases/1.5.1.md).
