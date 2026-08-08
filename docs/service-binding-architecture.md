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

The public `genericparser-vinted-poc.*.workers.dev` hostname is not used by the production adapter. Anonymous Vinted HTML/API requests remain fail-open fallbacks only.
