# GenericParser Architektur

## Zielbild

GenericParser exposes one stable, project-independent contract to Evercade, SNES PAL and future clients. Search profiles enter through `generic-parser-module-v1`; normalized listings, pagination, matching and traffic-light results leave through the same boundary.

## Production topology

```text
Evercade / SNES / generic client
              ↓
generic-parser-module-v1
              ↓
Cloudflare Python Worker + classification + PWA
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

The 1.4 eBay fields and 1.5 product-classification fields are additive. Existing clients can continue to consume the shared listing fields. Clients that understand eBay can additionally use `item_price`, `shipping_cost`, `total_price`, `buying_options`, `listing_format`, `auction`, `bid_count`, `item_end_date` and `transient`. Version 1.5 adds `product_classification` and the matching `result_info.product_class` fields without changing the module contract.

Every source is classified after normalization and before the additive traffic-light decision. Clear product mismatches become red, unknown product types become yellow, and existing bundle/profile rules remain authoritative. The browser groups results in the fixed order green, yellow, orange and red before applying the selected sort inside each group.

## eBay price invariant

Generic matching and the traffic light use the established `price` field. For eBay, `price` is deliberately set only when the delivered or pickup total is trustworthy:

```text
known shipping:  price = total_price = item_price + shipping_cost
pickup only:     price = total_price = item_price
unknown shipping: price = total_price = null; item_price remains visible
```

This prevents unknown shipping from being scored as zero-cost shipping.

## Secrets and data lifetime

`EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` are request-scoped Cloudflare bindings. OAuth access tokens are cached only in Worker isolate memory until shortly before expiry. Error messages are sanitized and never include credentials or tokens. The separate notification Worker receives the same credentials and `EBAY_DELETION_VERIFICATION_TOKEN` as encrypted secrets.

Ordinary eBay listing payloads are transient. The Worker has no listing database, and the bundled PWA filters eBay rows out before serializing search state to IndexedDB. Only a listing deliberately starred by the user is copied into a dedicated browser-local favorite store. That bounded snapshot omits descriptions, seller names, seller IDs, feedback and account identifiers.

The signed eBay Marketplace Account Deletion endpoint is isolated in `pocs/ebay-notifications`. It supports the exact GET challenge contract and verifies POST signatures with the official public-key API. Valid notifications are acknowledged with 204; username, user ID and EIAS token are neither logged nor stored.

## Vinted deferred details

Vinted detail enrichment remains separate from catalog pagination. The browser renders catalog results immediately, then sends incomplete Vinted items to `/api/vinted/enrich` in serial batches of at most three. Returned details are merged, reclassified and rescored. Starting a new search or stopping the current one cancels the pending client queue.

## Deployment and verification

Pull requests compile the runtime, execute the browser favorite-store test, validate eBay's official signature fixture and run stable-core, Vinted, eBay and classification regressions. The production workflow deploys the Vinted component, signed eBay notification Worker and Python Worker, then validates:

1. eBay notification health and the exact challenge response;
2. exact live release identity and eBay secret bindings;
3. Kleinanzeigen, Vinted Service Binding and official eBay Browse results in one search;
4. classification on every returned listing and no seller/account fields in eBay rows;
5. `EBAY_DE`, fixed-price default and conservative total-price mapping;
6. classification after the deferred Vinted detail batch.

Release metadata remains a candidate until this deployment workflow succeeds. Stable release metadata records the accepted production commit and workflow run and keeps the previous stable version as rollback target.
