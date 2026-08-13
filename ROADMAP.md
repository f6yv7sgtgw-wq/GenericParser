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

Current status: **1.9.5 release candidate** (2026-08-13), production acceptance
pending; 1.9.4 is the accepted stable baseline and the rollback target. 1.9.5
implements the consequence of the depth measurement: an empty Vinted catalog
page beyond the first (no challenge) is a natural source end — `status:
empty`, reason `vinted_anonymous_depth_reached`, no retries, no pointless
public-web fallback, and the source bar reads "Abgeschlossen · anonyme
Blättertiefe erreicht". The 60s/120s retry ladder remains for the transient
`vinted_browser_access_limited` flavour only. Next structural step stays the
1.9 server-side jobs line ("only new offers").

1.9.4
aligns the results area with the search mask width (the 1.3.4 breakout to
1460px left a fifth card column overhanging on wide monitors).

The Vinted ceiling is now fully explained (diagnostic run, 2026-08-13): a
vinted-only API run **without any browser background enrichment** hit exactly
the same wall — 10 catalog pages, 250 listings, blocked on page 10, both
staggered retries (60s/120s) unsuccessful. The enrichment traffic is
exonerated; the limit is the **anonymous catalog depth of ~10 pages**, not a
volume or rate budget. Two block flavours exist in the logs:
`vinted_browser_access_limited` (transient — this one reopened once after
67s in the 1.9.2 run) and `no_public_listings_parsed` at page ≥ 10 (the
depth end — never reopens). Consequences: (a) a candidate 1.9.5 could treat
the depth end as a natural `source_complete` ("anonyme Blättertiefe
erreicht") instead of spending ~3 minutes on hopeless retries, keeping
retries only for the transient flavour; (b) the structural answer remains
the 1.9 server-side jobs line — Vinted sorts `newest_first`, so periodic
"only new offers" runs make the 10-page depth irrelevant.

The 1.9.3 acceptance run `f zero snes` proved the staggered
retries (measured 64.7s and 124.9s) — Vinted did not reopen. 1.9.3
adds a listing-age window as a regular search criterion (browser defaults to
the last 90 days with options from 15 days to "all"; additive `max_age_days`
with default null in the contracts; undated listings always pass), staggers
the Vinted block retries (60s, then 120s, then a final honest `blocked`), and
makes the per-source status describe its lifecycle — not started, working,
completed, plus errors and warnings — instead of announcing "Erfolgreich"
after every intermediate packet.

1.9.2 (accepted 2026-08-13) lets a blocked Vinted resume, and the
acceptance run `snes` (7050 results, 494 packets) proved the mechanism: the
first blockade was reopened 67s later by the retry with a fresh bootstrap
(two more ok packets, retry budget reset), the second blockade survived both
attempts and the source ended honestly blocked. Total Vinted yield stayed at
~250 listings — the volume budget appears to be cumulative across bootstraps,
so the resume recovers individual packets but does not lift the ceiling. If
more yield is needed, a longer retry cooldown learned from event logs is the
next measurable lever. The deploy flakiness (Pyodide download, `refused
stream`) struck a second time and the deploy step now retries up to three
times.

1.9.1 (accepted 2026-08-13, run `levis 501 w34 l34`, 4770 unique
results, no retries) showed Kleinanzeigen ending truthfully with
`source_complete` after 5 packets, eBay running 219 packets to its real
natural end, and Vinted packets spaced 25–27s apart as designed. 1.9.1
implements the Vinted rotation cooldown (20s between Vinted packets, the other
sources rotate without pauses, a pacing hint lets the browser wait visibly
when only Vinted remains), corrects the per-source stop reason — the
"Kleinanzeigen packet budget" turned out to be the packet-level v2 stop reason
misattributed to sources that ended mid-run — and hardens 1.9.0's relevance
check with spelling-variant tolerance (`relevance-v2`: Lemminge/Tribess match,
wario/karte still don't). The Vinted enrichment rescore now applies the
relevance rule, "nur Anleitung"-style listings classify as accessories, and
the runtime loader fallbacks write event-log entries instead of degrading
silently.

1.9.0 added the source-neutral relevance check from `docs/HANDOVER-1.9.0.md`:
a search for `super mario kart 8` returned 1291 results that the classifier
had no reason to reject, because it judges the product kind, not the fit to
the query. The new `relevance.py` measures how well the carrying query terms
are covered in the title and maps low coverage to red/yellow additively —
never silently hiding a result. The acceptance run `lemmings snes` returned
249 results with 97 marked red and hidden only by the status filter.

The Vinted question is now measured, not guessed: despite the 25–27s spacing
the source still blocked after 10 full packets / exactly 250 listings — the
same yield as without the cooldown. The anonymous session limit is
volume-based (~250 listings per bootstrap), not rate-based. 1.9.2 implements
the consequence: a blocked Vinted retries with a fresh bootstrap instead of
ending for good. Whether Vinted actually reopens after the 60s retry cooldown
is the open measurement for the 1.9.2 acceptance run; if it does not, the
next candidate lever is a longer retry cooldown learned from event logs.

Earlier status: 1.8.6 is the accepted stable
baseline and the rollback target. 1.8.7 records why each source stops and
makes the event log downloadable, so the observed per-source ceilings can be
diagnosed from evidence instead of guessed at. 1.8.6 fixes an interaction the rotation
exposed: a single shared inter-packet delay let the slowest source throttle
all the others, and the throttle itself was only ever disabled by an external
assignment that failed silently. 1.8.0 closes the remaining 1.7 scope and adds
work requested from production use:

- condition and delivery are normalized into source-neutral codes, exposed
  additively as `condition_code` and `delivery.mode`, so filters stop matching
  display text. `like_new` becomes its own code instead of counting as new;
- Kleinanzeigen bundles that list individual items with individual prices are
  resolved into derived per-item tiles that keep the original advert URL;
- Vinted catalog cards carry their photo, so the grid fills with the first
  packet instead of waiting for the detail queue;
- the browser is rebuilt around a modern search mask with a collapsible filter
  panel and loading placeholders.

1.8.5 completes the line: the marketplace sources now rotate instead of being
drained one after another, and `tests/fixtures/normalization_cases.json` gives
the normalizers a shared deterministic case collection that both the Python
adapters and the Vinted worker are checked against.

Earlier status: **1.7.1 stable and production-accepted** (2026-08-12). 1.7.1 runs the deferred Vinted
detail batches two at a time instead of strictly one after another, with a
per-request abort controller and a retryable rate limit, without giving
background work priority over the primary packet stream. It changes no schema,
contract or search semantics. Live acceptance confirmed six auctions among
twenty-five eBay results with the option on and none with it off, the additive
`size` field on every listing, and Vinted sizes already coming from catalog
cards. 1.6.2 remains the rollback target.

1.7.0 remains the functional step of this line. 1.6.2 remains the production
rollback target. 1.7.0 turns offer format and size into properties of a result
set instead of hidden search preconditions: eBay auctions are searched by
default and hidden by a `no-auction` result filter, and the Vinted size is
normalized into an additive module-v2 `size` field with a browser size facet
that keeps "no size given" distinguishable from a label. Module-v1 and
module-v2 request defaults stay unchanged, so `include_auctions` remains opt-in
for API consumers. Production acceptance is pending; the size extraction
additionally requires a deployment of the separate Vinted browser worker.

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
