# Vinted transport contract

The Browser component remains an implementation detail. GenericParser depends on a service binding named `VINTED_BROWSER`, not a hostname.

Catalog response fields are `status`, `listings`, optional `browser`, `enrichment`, `component`, `revision`, `complete`, `nextPage`, and `targetUrl`.

The additive deferred-detail operation uses internal path `/enrich` with one to three repeated `item` query parameters. Each value must be a canonical HTTPS Vinted item URL. Its response contains `status`, `mode=deferred-detail-batch`, `detailBatchLimit`, `listings`, `enrichment`, `component`, `revision`, and `elapsedMs`.

GenericParser normalizes both operations into the existing module-v1 listing shape. Deferred results additionally use `detail_enrichment.mode=background-batch` and are re-scored before they are returned to the client. A component failure is fail-open and does not invalidate the catalog response.
