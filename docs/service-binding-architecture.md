# Vinted Service Binding

`genericparser` binds `VINTED_BROWSER` directly to `genericparser-vinted-poc` in Cloudflare.

Request path:

1. Browser/client calls GenericParser `/search`.
2. `cloudflare_worker.Default.fetch` obtains `env.VINTED_BROWSER`.
3. The binding is installed in a request-local `ContextVar`.
4. Multi-source runtime calls `search_vinted`.
5. Vinted adapter calls `VINTED_BROWSER.fetch()` using an internal synthetic URL.
6. The Browser Run worker queries Vinted and returns its component JSON contract.
7. GenericParser normalizes those listings into `generic-parser-module-v1` results.
8. The request-local binding is reset after ASGI completes.

Deferred detail path in 1.3.2:

1. The browser or a module-v1 client receives and renders the catalog response.
2. It sends at most three returned Vinted listings to `/api/vinted/enrich` or `/api/module/v1/vinted/enrich`.
3. GenericParser validates Vinted origin, item path and ID consistency.
4. The adapter calls the same private binding with `/enrich?item=...` parameters.
5. Browser Run opens the three item pages in parallel and returns detail fields.
6. GenericParser merges the fields and re-runs matching and traffic-light scoring.
7. The client serializes the next batch; catalog pagination was never awaiting this path.

The public `genericparser-vinted-poc.*.workers.dev` hostname is not used by the production adapter. Anonymous Vinted HTML/API requests remain fail-open fallbacks only. The Browser Run worker still exposes a public health/search surface for deployment verification, but GenericParser production traffic never depends on it.
