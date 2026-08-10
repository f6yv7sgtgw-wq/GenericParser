# GenericParser API 1.5.0

Version: `1.5.0`  
Build: `gp-150-20260810-1`  
Contract: `generic-parser-module-v1`

## Compatibility

All 1.4.0 request fields and endpoint paths remain available. The
`generic-parser-module-v1` contract is unchanged. Version 1.5.0 adds
classification fields to listings and additional capability metadata; these
fields are additive.

The Kleinanzeigen 0.44.4 extraction/pagination core, Vinted Service Binding,
official eBay Browse API, fixed-price default and conservative total-price
semantics remain in place.

## Product classification

Every returned listing contains:

```json
{
  "product_classification": {
    "code": "main_product",
    "label": "Hauptprodukt",
    "confidence": "high",
    "relevance": "accept",
    "expected_code": "main_product",
    "signals": ["evercade"],
    "reason": "Produktart entspricht der Suche: Hauptprodukt",
    "ruleset": "product-classification-v1"
  },
  "result_info": {
    "product_class": "main_product",
    "product_class_label": "Hauptprodukt"
  }
}
```

Supported codes:

- `main_product`
- `accessory_part`
- `bundle`
- `wanted`
- `rental`
- `service`
- `related_merchandise`
- `unknown`

Known mismatched classes become rejected results. Unknown classes remain
review results. Bundles continue to obey the existing `accept_bundles` profile
switch. A query that explicitly requests an accessory or merchandise class is
not rejected merely because it is not a game.

## Result order and browser filters

The bundled browser always groups results in this order:

1. green
2. yellow
3. orange
4. red

The selected relevance/date/price sort applies within each group. Browser-only
filters cover traffic light, source, product class, condition, trustworthy
total price, shipping, single/bundle scope and offer format. Red results are
hidden by default but are retained in the loaded result set and can be shown.

## Explicit favorites

`/favorites.html` reads a dedicated browser-local favorite store. A listing is
written only after the user presses its star. The snapshot is limited to:

- listing ID, title, canonical HTTPS URL and image URL;
- source, price and shipping fields;
- condition, scope, listing format, traffic-light and product-class labels;
- save timestamp.

Descriptions, seller usernames, seller IDs, feedback data and eBay account
identifiers are never included. eBay search-state persistence remains disabled;
favorites are separate explicit user selections and are not synchronized
between browsers or devices.

## eBay Marketplace Account Deletion endpoint

Endpoint:

`https://genericparser-ebay-notifications.f6yv7sgtgw.workers.dev/marketplace-account-deletion`

- `GET ?challenge_code=...` returns the required SHA-256
  `challengeResponse` for eBay endpoint validation.
- `POST` accepts only `MARKETPLACE_ACCOUNT_DELETION` JSON messages with a valid
  `X-EBAY-SIGNATURE`.
- The component obtains eBay public keys through the official Notification API,
  caches them for one hour and verifies the ECDSA signature.
- Valid notifications receive HTTP 204. Invalid signatures receive HTTP 412.
- Notification username, user ID and EIAS token are neither logged nor stored.

Required encrypted component secrets:

- `EBAY_CLIENT_ID`
- `EBAY_CLIENT_SECRET`
- `EBAY_DELETION_VERIFICATION_TOKEN`

The verification token must be the same 32–80 character value entered in the
eBay developer portal.

## Capabilities

`GET /api/module/v1/capabilities` now advertises `classification`, `ui`, explicit
favorite persistence and the notification endpoint while retaining all three
default sources.
