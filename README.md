# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für **Evercade**, **SNES-PAL-Sammlung** und weitere Projekte.

## Aktueller Stand

- **Version:** `0.45.1`
- **Build-ID:** `gp-0451-20260807-1`
- **Modulvertrag:** `generic-parser-module-v1`
- **Stabile Rückfallreferenz:** `0.44.6.5`
- **Fachlicher Suchkern:** unverändert `0.44.4`
- **Suchservice:** unverändert `search_service_v0450`
- **Zielplattform:** Cloudflare Workers Free
- **Release-Typ:** Stabilitäts- und Infrastruktur-Release

Vollständige Release-Unterlagen:

- [API-, Infrastruktur- und Limitierungsdokumentation 0.45.1](docs/API_0.45.1.md)
- [Release Notes 0.45.1](docs/releases/0.45.1.md)
- [Deployment und Live-Abnahme](docs/DEPLOYMENT.md)
- [Release-Prozess](docs/RELEASE_PROCESS.md)

## Ziel von 0.45.1

0.45.1 verändert **nicht**, wie Kleinanzeigen gesucht, gefiltert, bewertet oder paginiert wird. Der Release stabilisiert ausschließlich Browser↔Worker-Kommunikation und Betrieb:

- globale CORS-Behandlung
- browserkompatible `OPTIONS`-Preflights
- zentrale Request-ID
- strukturiertes Request-Logging
- Health-, Version- und Diagnostics-Endpunkte
- konsistente Suchrouten und Alias-Endpunkte
- Vor- und Nach-Deployment-Prüfungen

## Endpunkte

Diagnose:

- `GET /health`
- `GET /version`
- `GET /api/version`
- `GET /diagnostics`

Suche:

- `POST /search`
- `POST /api/search`
- `POST /api/module/search`
- `POST /api/module/v1/search`

Modul:

- `GET /api/module/v1/capabilities`
- `POST /api/module/v1/profile/validate`
- `GET /api/module/v1/self-test?enabled=true`

## CORS und Browserkompatibilität

Alle Worker-Antworten tragen einheitliche `Access-Control-Allow-*`-Header. `OPTIONS` wird global beantwortet. Die Browserdiagnose kann dadurch CORS-/Preflight-Probleme eindeutig von Routing-, Worker- oder Suchproblemen unterscheiden.

## Logging

Jeder Worker-Request protokolliert serverseitig Request-ID, Timestamp, Route, Methode, Origin, User-Agent, Laufzeit, HTTP-Status und Trefferzahl. Bei Fehlern werden Fehlertyp und Stacktrace im Workerlog protokolliert. Stacktraces werden nicht ungefiltert an Browserclients übertragen.

## Kompatibilität

`generic-parser-module-v1` bleibt unverändert. Evercade Next und SNES PAL können bestehende Profile und Ergebnisverträge weiterverwenden. `/api/search` und `/api/module/v1/search` bleiben kompatibel; `/search` und `/api/module/search` kommen als browserfreundliche Aliase hinzu.

## Unverändert gegenüber 0.45.0

- Suchalgorithmus
- Matching und Scoring
- Ranking
- Preisbewertung
- Kleinanzeigen als einzige automatische Quelle
- maximal sieben Karten pro Arbeitspaket
- echte Kleinanzeigen-Pagination
- Deduplizierung
- Ampellogik
- Retry-/Recovery-Verhalten

## Cloudflare Workers Free

Die dokumentierten Free-Tarif-Grenzen und Auswirkungen stehen vollständig in [`docs/API_0.45.1.md`](docs/API_0.45.1.md). Maßgeblich sind die offiziellen Cloudflare-Limits: https://developers.cloudflare.com/workers/platform/limits/

## Release-Prüfung

```bash
python scripts/check_release_metadata.py
python scripts/run_release_tests.py
python -m py_compile src/generic_parser/cloudflare_v0451.py
node --check cloudflare/public/build-identity-0451.js
```

Der Produktionsworkflow `.github/workflows/cloudflare-deploy.yml` deployt nach erfolgreicher Prüfung den exakten `main`-Commit und testet anschließend Health, Version, Diagnostics, CORS/Preflight, Browserassets und ein begrenztes echtes Live-Arbeitspaket.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md), [`VERSION.json`](VERSION.json) und [`docs/RELEASE_INDEX.md`](docs/RELEASE_INDEX.md).
