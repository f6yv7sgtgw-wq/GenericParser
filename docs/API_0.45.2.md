# GenericParser 0.45.2 – API-, Infrastruktur- und Limitierungsdokumentation

Build: `gp-0452-20260807-1`  
Modulvertrag: `generic-parser-module-v1`

## Ziel

0.45.2 ist ein Browser-/Worker-Infrastruktur-Hotfix. Er behebt die Fehlerklasse, bei der Evercade Next oder SNES im Browser für alle Worker-Endpunkte nur `Load failed` sehen. Suchalgorithmus, Matching, Ranking, Preisbewertung, Pagination, 7er-Arbeitspakete und Recovery bleiben unverändert.

## Edge-Shell

Der Cloudflare-Entrypoint beantwortet die folgenden Infrastrukturpfade ohne FastAPI-, Pydantic- oder Suchmodul-Import:

- `GET /health`
- `GET /version`
- `GET /api/version`
- `GET /diagnostics`
- `OPTIONS *`

Damit bleiben Erreichbarkeit, Version und CORS diagnostizierbar, selbst wenn der nachgelagerte ASGI-Bootstrap fehlschlägt. In diesem Fall erhalten Browser statt eines Netzwerkfehlers eine strukturierte JSON-Antwort mit HTTP 503 und CORS-Headern.

## Suchendpunkte

- `POST /search`
- `POST /api/search`
- `POST /api/module/search`
- `POST /api/module/v1/search`

Die Suche wird weiterhin an `cloudflare_v0451` und `search_service_v0450` delegiert. Der fachliche Referenzkern bleibt 0.44.4, die operative Rückfallreferenz 0.44.6.5.

## CORS

Jeder Preflight wird vor dem ASGI-Import beantwortet. Erlaubt werden:

- Origin: `*`
- Methoden: `GET, POST, OPTIONS`
- Header: `Accept`, `Content-Type`, `X-GenericParser-Contract`, `X-GenericParser-Token`, `X-GenericParser-Debug`, `X-GenericParser-Tests`, `X-Request-ID`
- Exposed Header: Request-ID, Version, Build, Vertrag und CF-Ray

Der Deployment-Test sendet echte Browser-Preflights für `/api/module/search`, `/api/search` und `/search` mit dem Evercade-Origin.

## Diagnose und Logging

Der Edge-Shell-Logeintrag enthält Request-ID, Timestamp, Route, Methode, Origin, User-Agent, HTTP-Status, Phase und Fehler. `/diagnostics` meldet zusätzlich Edge-Runtime, Routing, CORS, Preflight, Modulvertrag und ob der ASGI-Pfad bereits geladen wurde.

## Evercade und SNES

Evercade Next und SNES PAL verwenden weiter `generic-parser-module-v1`. Es gibt keine Vertragsänderung und keine neue Suchlogik. 0.45.2 verändert ausschließlich die Transport- und Diagnosegrenze zwischen Browser und Worker.

## Deployment-Abnahme

Vor Deploy werden Metadaten, Syntax, Browserassets und die vollständige netzwerkfreie Release-Suite geprüft. Nach Deploy müssen `/health`, `/version`, `/diagnostics`, drei Browser-Preflights, Browserassets und ein reales Modul-Arbeitspaket erfolgreich sein.

## Bekannte Grenzen

- 0.45.2 kann einen nicht existierenden DNS-Namen oder eine vollständig deaktivierte `workers.dev`-Subdomain nicht innerhalb des Workers reparieren; der Deployment-Check schlägt dann sichtbar fehl.
- Der Suchpfad bleibt an die bekannten Cloudflare-/Upstream-Grenzen des Referenzkerns gebunden.
- Der Edge-Shell ersetzt keine serverseitige Queue und keine dauerhafte Persistenz.
- `Access-Control-Allow-Origin: *` setzt voraus, dass Browserrequests ohne Cookie-Credentials arbeiten; der optionale App-Token wird über einen explizit erlaubten Header übertragen.

## Cloudflare Workers Free

Für dieses Release gelten weiterhin die dokumentierten Free-Tarif-Grenzen: 100.000 Requests pro Tag, 10 ms CPU je HTTP-Request, 128 MB Speicher, 50 Subrequests je Invocation, sechs gleichzeitige ausgehende Verbindungen, 3 MB komprimierte Workergröße, eine Sekunde Startup-Zeit und 256 KB Logs pro Request. Quelle: https://developers.cloudflare.com/workers/platform/limits/

Diese Grenzen sind ein Grund dafür, den Suchkern nicht zu verändern und weiterhin kleine Arbeitspakete zu verwenden.
