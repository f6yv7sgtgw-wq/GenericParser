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

Current status: **1.3.4 release candidate**. Search behavior remains unchanged; production deployment and live acceptance are pending. 1.3.3 remains the rollback target.

## 1.4 – Title and cartridge normalization

- normalize Evercade and SNES PAL titles;
- spelling variants, numbers and editions;
- identify individual modules contained in bundles.

## 1.5 – Search profile expansion

- structured profiles for missing cartridges;
- consistent transfer of result, traffic-light and offer data;
- prepare multiple providers behind the same module contract without changing client APIs.

## 1.6 – Deal engine

- compare price with market value and maximum price;
- condition, completeness and shipping;
- deal classes and total price.

## 1.7 – Server-side search jobs

- evaluate queue/workflow/Durable Object architecture;
- persistent work packets independent from browser lifetime;
- only new or changed offers;
- result and price history;
- notifications for Evercade and SNES.

## 1.8 – Operations and quality

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
