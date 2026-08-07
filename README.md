# GenericParser

Stable reusable Kleinanzeigen parser module and browser UI for **Evercade**, **SNES PAL Sammlung** and future projects.

## Stable release

- **Version:** `1.0.0`
- **Build:** `gp-100-20260808-1`
- **Status:** Stable
- **Worker profile:** Cloudflare Workers Paid
- **Module contract:** `generic-parser-module-v1`
- **Search runtime:** `0.45.0`
- **Functional search core:** `0.44.4`
- **Operational reference:** `0.44.6.5`

GenericParser 1.0.0 promotes the proven 0.45.2 Build 7 Paid Worker baseline. The search core, matching, extraction, pagination and traffic-light evaluation are not rewritten for 1.0.

## Architecture

```text
Evercade / SNES / other client
        ↓
generic-parser-module-v1
        ↓
GenericParser Worker
        ↓
Kleinanzeigen search runtime
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
- `GET /api/module/v1/self-test?enabled=true`

## Paid Worker profile

Free-Worker protection waits are disabled:

- new-search cooldown: `0 ms`
- normal packet delay: `0 ms`
- retry waits: `0 ms`
- auto-resume quiet period: effectively immediate
- recovery health interval: effectively immediate

The proven seven-result work-packet structure remains unchanged; only artificial waiting between requests was removed.

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
9. exact-source ZIP artifact.

## Versioning

From 1.0 onward GenericParser uses semantic versioning. Search-core changes are explicit functional changes; infrastructure changes must not silently change matching, ranking, extraction or pagination.

Further documentation: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md), [`VERSION.json`](VERSION.json), [`docs/RELEASE_INDEX.md`](docs/RELEASE_INDEX.md) and [`docs/releases/1.0.0.md`](docs/releases/1.0.0.md).
