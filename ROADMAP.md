# GenericParser Roadmap

## 1.0.0 – Stable baseline

Status: **Stable**.

GenericParser 1.0.0 is the production baseline. It promotes the proven Paid Worker state without changing the functional search core.

Stable guarantees:

- `generic-parser-module-v1` remains the integration contract;
- Evercade and SNES PAL adapters remain supported;
- search runtime remains based on the proven 0.45.0 implementation;
- functional search core remains 0.44.4;
- operational reference remains 0.44.6.5;
- seven-result work packets remain;
- artificial Free Worker waiting times are disabled on the paid profile;
- CORS, diagnostics, deployment identity and live verification are release requirements.

## 1.1 – Multi-source foundation

- completed multi-source response and source-specific UI identity;
- kept contract-based compatibility for Evercade and SNES PAL;
- prepared Vinted as the second production source.

## 1.2 – Vinted production transport

- completed Browser Run catalog access;
- moved production traffic to private `VINTED_BROWSER` Service Binding;
- kept anonymous public-web access as fail-open fallback only;
- removed public Browser Worker URLs from the production adapter.

## 1.3 – Vinted detail quality

- 1.3.0: detail-page image, price, description and condition; superseded after the live request reached about 49 seconds;
- 1.3.1: stable critical-path limit of three detail pages per catalog request;
- 1.3.2: serial background batches of three, in-place card updates and rescoring without blocking catalog pagination.
- 1.3.3: Evercade/SNES-aligned browser UI, header-level Log and Diagnose navigation, and compact expandable Vinted descriptions without hashtag-only blocks.
- 1.3.4: dense responsive result grid, substantially smaller side-by-side media cards and removal of the decorative search-header mark.

Current status: **1.3.4 stable and production-accepted**. Dense responsive UI contracts, live identity, multi-source search and deferred Vinted enrichment passed on 2026-08-09; 1.3.3 remains the rollback target.

## 1.4 – eBay production integration

- use the official eBay Browse API on marketplace `EBAY_DE`;
- add eBay as the third default, fail-open source;
- default to fixed-price listings and make auctions an explicit opt-in;
- score only a trustworthy total when shipping is known;
- keep OAuth tokens in memory and never persist ordinary eBay search-state data.

Current status: **1.4.0 stable and production-accepted**. The one-shot access gate and the regular deployment workflow both passed; live verification covered all three sources, eBay fixed-price and total-price invariants, and the existing deferred Vinted detail path. 1.3.4 remains the rollback target.

## 1.5 – Product classification

- distinguish main products, accessories/parts, bundles, wanted ads, rentals, services and unrelated merchandise;
- make classifier evidence visible to callers and use known category information from eBay;
- keep green results first, independent from the selected within-group sort;
- add result filters, explicit browser-local favorites and the required signed eBay account-deletion endpoint;
- retain deterministic review behavior for uncertain offers.

Current status: **1.5.1 stable and production-accepted**. The patch corrects the manual-stop status and refines the responsive filter layout without changing classification, all three sources, favorites or the module contract. Production workflow `31365503492` passed the signed eBay notification contract, live identity, all three marketplace sources and deferred Vinted details; 1.5.0 remains the rollback target.

## 1.6 – Project-independent API and browser usability

- add `generic-parser-module-v2` without removing or changing module-v1;
- process one source page per request and resume with signed, opaque tokens;
- normalize listing identity, known-total pricing and source status;
- use the same v2 route in the bundled browser;
- separate search criteria from result filtering;
- add term chips, source progress, active filters, recent searches and stronger mobile behavior.

Current status: **1.6.3 release candidate**. 1.6.2 remains the production
rollback target. 1.6.3 classifies Safari `Load failed` as a retryable transport
interruption during long API-v2 runs, preserves transient eBay listings when
the same page resumes, lets deferred Vinted details yield to the primary
packet stream and reports unique per-source and aligned Vinted progress.
Successful packets retain the Paid Worker profile with zero artificial delay;
production long-run acceptance is pending.

## 1.7 – Source quality and schema evolution

- improve source-neutral condition, delivery and offer-format normalization;
- version additive listing fields without changing existing v2 meanings;
- expand deterministic fixtures for spelling, punctuation and marketplace edge cases;
- keep catalog, collection, valuation and deal decisions in consuming clients.

## 1.8 – Client integration quality

- publish additional end-to-end examples for browser and embedded consumers;
- improve observable retry guidance and source degradation diagnostics;
- add contract conformance fixtures for independent clients;
- preserve project-neutral requests and responses.

## 1.9 – Server-side search jobs

- evaluate queue/workflow/Durable Object architecture;
- persistent work packets independent from browser lifetime;
- only new or changed offers;
- optional result and price history with an explicit retention model;
- client-neutral notification hooks.

## 1.10 – Operations and quality

- permanent regression suite;
- reference searches for Evercade and SNES;
- operational dashboards and diagnostics;
- release/deployment checklist automation;
- explicit rollback artifacts for every stable release.

## Historical references

The pre-1.0 development line remains preserved in Git history and the changelog. Important references are:

- 0.44.4: functional search core;
- 0.44.6.5: operational reference;
- 0.45.0: module-v1 introduction;
- 0.45.2 Build 7 Paid Worker: final proven pre-1.0 production baseline.
