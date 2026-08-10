# GenericParser API 1.5.1

Version: `1.5.1`

Build: `gp-151-20260810-1`

Contract: `generic-parser-module-v1`

## Compatibility

The module contract, request fields, response fields and endpoint paths are
unchanged from 1.5.0. Kleinanzeigen extraction and pagination, Vinted Service
Binding enrichment, eBay Browse API transport, product classification, traffic
grouping and explicit favorites keep their existing behavior.

## Manual-stop state

A browser run stopped by the user remains incomplete and resumable:

```json
{
  "type": "search_stopped",
  "reason": "user_stopped",
  "complete": false,
  "resumable": true
}
```

The visible status is `Suche pausiert`. The saved search state stays available
to `Letzte Suche fortsetzen`. A manual stop is never labelled as a fully
completed search.

## Browser layout

The nine existing result-filter controls are unchanged. Their presentation is
now balanced into two complete rows on wide screens, three columns on smaller
desktop/tablet widths, two columns on normal phones and one column only below
360 CSS pixels. Red results remain hidden by default; green results remain the
first traffic-light group regardless of the selected within-group sort.

## Data handling

No persistence rule changed. Ordinary eBay results remain transient. Only a
listing deliberately starred by the user enters the bounded browser-local
favorite store, without description, seller or account identifiers. The signed
Marketplace Account Deletion endpoint remains active and stores no user data.
