# Vinted transport contract

The Browser component remains an implementation detail. GenericParser depends on a service binding named `VINTED_BROWSER`, not a hostname. Expected response fields are `status`, `listings`, optional `browser`, `component`, `revision`, and `targetUrl`. GenericParser normalizes each listing into the existing module-v1 listing shape.
