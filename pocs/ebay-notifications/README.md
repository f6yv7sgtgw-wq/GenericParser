# eBay Marketplace Account Deletion endpoint

Cloudflare Worker component for GenericParser 1.5. It implements the eBay
endpoint-validation challenge and verifies signed
`MARKETPLACE_ACCOUNT_DELETION` notifications with eBay's public-key API.

Production endpoint:

`https://genericparser-ebay-notifications.f6yv7sgtgw.workers.dev/marketplace-account-deletion`

Required encrypted Worker secrets:

- `EBAY_CLIENT_ID`
- `EBAY_CLIENT_SECRET`
- `EBAY_DELETION_VERIFICATION_TOKEN` (32–80 alphanumeric, underscore or hyphen)

The component never logs or stores username, user ID or EIAS token. GenericParser
favorites deliberately omit seller/account identifiers and are stored only in
the user's browser.
