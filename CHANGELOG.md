# Changelog

## 0.45.2 – 2026-08-07 – Browser Edge Hotfix

- `generic-parser-module-v1` unverändert beibehalten.
- Minimalen dependency-freien Edge-Shell direkt im Cloudflare-Entrypoint ergänzt.
- `/health`, `/version`, `/api/version` und `/diagnostics` werden ohne FastAPI-/Suchimport beantwortet.
- Sämtliche `OPTIONS`-Preflights werden vor dem ASGI-Bootstrap beantwortet.
- CORS-Header stehen auch auf strukturierten Bootstrap-Fehlerantworten zur Verfügung.
- ASGI/FastAPI wird für Anwendungstraffic lazy geladen; Bootstrapfehler werden als HTTP 503 JSON sichtbar statt als Browser-`Load failed`.
- Worker-first-Routing und Service-Worker-Bypass für alle API-/Diagnosepfade abgesichert.
- Build-Identität auf `0.45.2` / `gp-0452-20260807-1` aktualisiert.
- Deployment-Gate um echte Evercade-Origin-Preflights für `/api/module/search`, `/api/search` und `/search` erweitert.
- Live-Gate verlangt zusätzlich Health, Version, Diagnostics, aktuelle Browserassets und ein echtes Modul-Arbeitspaket.
- Suche, Matching, Ranking, Preisbewertung, Pagination, sieben Karten je Arbeitspaket, Retry, Recovery und Ampel unverändert gelassen.

## 0.45.1 – 2026-08-07 – Infrastrukturstabilisierung

CORS, Diagnose, Request-ID, Logging, API-Aliase und Deployment-Qualität wurden vereinheitlicht. Suchlogik und Modulvertrag blieben unverändert.

## 0.45.0 – 2026-08-05 – Modulversion

`generic-parser-module-v1`, Evercade-/SNES-Adapter, optionale Debugdiagnose und netzwerkfreie Selbsttests wurden eingeführt. Suchverhalten blieb auf der stabilen Referenzlinie.

## Referenzen

- operative tiefe Rückfallreferenz: 0.44.6.5
- fachlicher Suchkern: 0.44.4
- vollständige historische Details: Git-Historie und `docs/RELEASE_INDEX.md`
