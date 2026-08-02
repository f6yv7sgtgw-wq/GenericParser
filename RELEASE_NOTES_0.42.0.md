# GenericParser 0.42.0

## Ziel

Import-stabiler Cloudflare-Python-Worker mit konsistenter Build-Identität im gesamten Datenfluss.

## Änderungen

- Minimaler Bootstrap-Worker für `/health`, `/api/version` und `/api/import-status`.
- Parser, Matching, HTTPX und Quellenmodule werden erst innerhalb von `/api/search` geladen.
- Strukturierte Fehlerphasen: `request_json`, `lazy_import_search_module`, `search_request_validation`, `page_worker_search`, `bootstrap_asgi`.
- Einheitliche Identität: Version `0.42.0`, Build `gp-0420-20260802-1`, Vertrag `match-v6.1-page-worker`.
- Identitätsheader auf allen erreichbaren API-Antworten.
- Handshake prüft UI, Controller, Worker, Build, Vertrag und Lazy-Bootstrap.
- Eigener Eventlog-Speicher und vollständig neuer PWA-Cache.
- Statische Tests für Einstiegspunkt, Lazy-Import, Browser-Build und Cache-Inhalt.

## Live-Test

Nach Deployment muss zunächst `Deployment konsistent` erscheinen. Die erste Suche lädt den Seitenworker lazy. Ein Importfehler muss als JSON mit Phase `lazy_import_search_module` erscheinen und darf keine unstrukturierte Cloudflare-Fehlerseite erzeugen.
