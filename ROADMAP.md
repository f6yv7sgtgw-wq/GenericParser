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

## 1.1 – Client integration hardening

- complete Evercade Next validation against 1.0.0;
- complete SNES PAL validation against 1.0.0;
- remove exact build pinning from clients in favor of module-contract compatibility;
- common client error schema and diagnostics;
- regression fixtures for both projects.

## 1.2 – Product classification

- distinguish main product, accessory, replacement part, bundle, wanted ad, rental and service;
- project-specific classification rules;
- regression tests based on real Evercade, SNES and generic searches.

## 1.3 – Title and cartridge normalization

- normalize Evercade and SNES PAL titles;
- spelling variants, numbers and editions;
- identify individual modules contained in bundles.

## 1.4 – Search profile expansion

- structured profiles for missing cartridges;
- consistent transfer of result, traffic-light and offer data;
- prepare multiple providers behind the same module contract without changing client APIs.

## 1.5 – Deal engine

- compare price with market value and maximum price;
- condition, completeness and shipping;
- deal classes and total price.

## 1.6 – Server-side search jobs

- evaluate queue/workflow/Durable Object architecture;
- persistent work packets independent from browser lifetime;
- only new or changed offers;
- result and price history;
- notifications for Evercade and SNES.

## 1.7 – Operations and quality

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
