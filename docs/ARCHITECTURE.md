# GenericParser Architektur

## Zielbild

GenericParser exposes one stable, project-independent contract to Evercade, SNES PAL and future clients. Search profiles enter through `generic-parser-module-v1`; normalized listings, pagination, matching and traffic-light results leave through the same boundary.

## Production topology

```text
Evercade / SNES / generic client
              ↓
generic-parser-module-v1
              ↓
Cloudflare Python Worker + PWA
              ↓
Kleinanzeigen core │ Vinted Service Binding │ eBay Browse API
```

The active Worker orchestrates three independent sources:

- **Kleinanzeigen** keeps the proven 0.44.4 functional search core and its established work-packet behavior.
- **Vinted** uses the private `VINTED_BROWSER` Cloudflare Service Binding for catalog and bounded detail access. At most three detail pages run in the catalog request; remaining details use serial client-driven batches of three.
- **eBay** uses application OAuth and the official Production Browse API on `EBAY_DE`. It returns 25 results per page, defaults to fixed price and can include auctions only when requested.

Each source reports its own status. A Vinted or eBay failure is fail-open and does not discard successful results from another source.

## Contract and compatibility

The public module version remains `generic-parser-module-v1`. Runtime filenames retain historical version numbers because they are compatibility bridges, not public release identity. `src/generic_parser/release_identity.py` is the single source for release version, build and contract.

The 1.4 eBay fields are additive. Existing clients can continue to consume the shared listing fields. Clients that understand eBay can additionally use `item_price`, `shipping_cost`, `total_price`, `buying_options`, `listing_format`, `auction`, `bid_count`, `item_end_date` and `transient`.

## eBay price invariant

Generic matching and the traffic light use the established `price` field. For eBay, `price` is deliberately set only when the delivered or pickup total is trustworthy:

```text
known shipping:  price = total_price = item_price + shipping_cost
pickup only:     price = total_price = item_price
unknown shipping: price = total_price = null; item_price remains visible
```

This prevents unknown shipping from being scored as zero-cost shipping.

## Secrets and data lifetime

`EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` are request-scoped Cloudflare bindings. OAuth access tokens are cached only in Worker isolate memory until shortly before expiry. Error messages are sanitized and never include credentials or tokens.

eBay listing payloads are transient. The Worker has no listing database, and the bundled PWA filters eBay rows out before serializing search state to IndexedDB. This is an explicit 1.4 behavior and not a later cleanup step.

## Vinted deferred details

Vinted detail enrichment remains separate from catalog pagination. The browser renders catalog results immediately, then sends incomplete Vinted items to `/api/vinted/enrich` in serial batches of at most three. Returned details are merged and rescored. Starting a new search or stopping the current one cancels the pending client queue.

## Deployment and verification

Pull requests compile the runtime, check browser JavaScript and run stable-core, Vinted and eBay regressions. The production workflow deploys both Workers and then validates:

1. exact live release identity and eBay secret bindings;
2. Kleinanzeigen, Vinted Service Binding and official eBay Browse results in one search;
3. `EBAY_DE`, fixed-price default and conservative total-price mapping;
4. the existing deferred Vinted detail batch.

Release metadata remains a candidate until this deployment workflow succeeds. Stable release metadata records the accepted production commit and workflow run and keeps the previous stable version as rollback target.
