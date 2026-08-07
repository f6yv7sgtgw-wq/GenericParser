# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für **Evercade**, **SNES-PAL-Sammlung** und weitere Projekte.

## Aktueller Stand

- **Version:** `0.45.2`
- **Build-ID:** `gp-0452-20260807-1`
- **Modulvertrag:** `generic-parser-module-v1`
- **Release-Typ:** Browser-/Worker-Infrastruktur-Hotfix
- **Technische Basis:** `0.45.1`
- **Stabile tiefe Rückfallreferenz:** `0.44.6.5`
- **Fachlicher Suchkern:** unverändert `0.44.4`
- **Suchservice:** unverändert `search_service_v0450`

Vollständige Unterlagen:

- [API-, Infrastruktur- und Limitierungsdokumentation 0.45.2](docs/API_0.45.2.md)
- [Release Notes 0.45.2](docs/releases/0.45.2.md)
- [Deployment und Live-Abnahme](docs/DEPLOYMENT.md)
- [Release-Prozess](docs/RELEASE_PROCESS.md)

## Was 0.45.2 behebt

Evercade Next konnte seine Queue vollständig abarbeiten, erhielt vom GenericParser im Browser jedoch für Health, Version, Diagnostics, Preflight und Suche nur `Load failed`. 0.45.2 setzt deshalb einen minimalen Cloudflare-Edge-Shell vor die bestehende ASGI-Anwendung.

Der Edge-Shell beantwortet `GET /health`, `GET /version`, `GET /api/version`, `GET /diagnostics` und alle `OPTIONS`-Requests **ohne** FastAPI-, Pydantic- oder Suchmodul-Import. Anwendungstraffic wird erst danach lazy an den bestehenden 0.45.1-ASGI-Pfad delegiert. Scheitert dieser Bootstrap, erhält der Browser eine CORS-fähige JSON-503-Antwort statt eines undiagnostizierbaren Netzwerkfehlers.

## Öffentliche Endpunkte

Diagnose: `GET /health`, `GET /version`, `GET /api/version`, `GET /diagnostics`.

Suche: `POST /search`, `POST /api/search`, `POST /api/module/search`, `POST /api/module/v1/search`.

Modul: `GET /api/module/v1/capabilities`, `POST /api/module/v1/profile/validate`, `GET /api/module/v1/self-test?enabled=true`.

## CORS

Preflight wird direkt im Worker-Entrypoint beantwortet. Unterstützt werden `GET`, `POST`, `OPTIONS` und die von Evercade/SNES benötigten Header einschließlich `Content-Type`, `X-GenericParser-Token`, `X-GenericParser-Contract` und `X-Request-ID`.

## Unverändert

0.45.2 verändert weder Suche noch Bewertung. Unverändert bleiben `generic-parser-module-v1`, `search_service_v0450`, Suchkern 0.44.4, Pagination, sieben Ergebnisse je Arbeitspaket, normale Pause, Matching, Ranking, Preisbewertung, Ampel, Retry, Recovery sowie Evercade-/SNES-Adapter.

## Tests und Deployment

```bash
python scripts/check_release_metadata.py
python scripts/run_release_tests.py
```

Der Produktionsworkflow deployt exakt den getesteten Main-Commit und führt danach einen Live-Gate aus: Health, Version, Diagnostics, Browser-CORS-Preflights für `/api/module/search`, `/api/search` und `/search`, Browserassets sowie ein reales Modul-Arbeitspaket.

## Cloudflare Workers Free

Die dokumentierten Free-Tarif-Grenzen bleiben relevant: 100.000 Requests/Tag, 10 ms CPU je HTTP-Aufruf, 128 MB Speicher und 50 Subrequests je Invocation. Details und bekannte Grenzen stehen in [`docs/API_0.45.2.md`](docs/API_0.45.2.md).
