# Rollback 1.2.2

If the Cloudflare Service Binding is not supported by the deployed Python Worker configuration or the live gate cannot obtain Vinted results, do not accept 1.2.2 as stable. Roll back the main worker to 1.2.1; the isolated `genericparser-vinted-poc` Worker is unaffected.
