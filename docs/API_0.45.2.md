# GenericParser 0.45.2 – API-, Infrastruktur- und Limitierungsdokumentation

Build: `gp-0452-20260807-2`  
Modulvertrag: `generic-parser-module-v1`

## Ziel

0.45.2 ist ein Browser-/Worker-Infrastruktur-Hotfix für Evercade Next und SNES. Suchalgorithmus, Matching, Ranking, Preisbewertung, Pagination, 7er-Arbeitspakete und Recovery bleiben unverändert.

## Befund aus Build 1

Build 1 (`gp-0452-20260807-1`) bestätigte live, dass der dependency-freie Edge-Shell funktioniert: `/health` war erreichbar und meldete korrekt 0.45.2. Der anschließende echte Suchpfad über die 0.45.1-ASGI-Infrastruktur endete jedoch mit Cloudflare Error 1101. Build 2 behält deshalb den erfolgreichen Edge-Shell bei, delegiert Anwendungstraffic aber an den zuvor live bewährten 0.45.0-ASGI-Pfad.

## Edge-Shell

Ohne FastAPI-, Pydantic- oder Suchmodul-Import werden beantwortet:

- `GET /health`
- `GET /version`
- `GET /api/version`
- `GET /diagnostics`
- `OPTIONS *`

Damit sind Worker-Erreichbarkeit, Version und CORS unabhängig vom Suchruntime-Bootstrap diagnostizierbar.

## Suchruntime Build 2

`cloudflare_v0452` importiert die bewährte 0.45.0-App aus `cloudflare_v0450` und ergänzt ausschließlich die beiden Aliasrouten `/search` und `/api/module/search`. Der Suchservice bleibt `search_service_v0450`; fachlicher Referenzkern bleibt 0.44.4 und die tiefe operative Rückfallreferenz 0.44.6.5.

Öffentliche Suchendpunkte:

- `POST /search`
- `POST /api/search`
- `POST /api/module/search`
- `POST /api/module/v1/search`

## CORS

Jeder Preflight wird vor dem ASGI-Import beantwortet. Erlaubt werden Origin `*`, Methoden `GET, POST, OPTIONS` sowie die von Evercade und SNES benötigten Request-Header einschließlich `Content-Type`, `X-GenericParser-Contract`, `X-GenericParser-Token` und `X-Request-ID`.

Der Live-Gate testet Browser-Preflights für `/api/module/search`, `/api/search` und `/search` mit dem Evercade-Origin.

## Diagnose und Logging

Edge-Logs enthalten Request-ID, Timestamp, Route, Methode, Origin, User-Agent, HTTP-Status, Phase und Fehler. `/diagnostics` meldet Edge-Runtime, Routing, CORS, Preflight, Modulvertrag und die verwendete Suchruntime `0.45.0`.

## Evercade und SNES

Evercade Next und SNES PAL verwenden unverändert `generic-parser-module-v1`. Weder Profile noch Ergebnisvertrag oder fachliche Suchlogik werden durch Build 2 verändert.

## Deployment-Abnahme

Vor Deploy: Metadatenprüfung, Python-Syntax, Browserasset-Syntax und vollständige netzwerkfreie Release-Suite. Nach Deploy: `/health`, `/version`, `/diagnostics`, Browser-CORS-Preflights, aktuelle Browserassets und ein reales Evercade-Modul-Arbeitspaket.

## Bekannte Grenzen

- Cloudflare- oder Upstream-Limits des bestehenden Suchkerns bleiben bestehen.
- Der Edge-Shell ersetzt keine serverseitige Queue oder dauerhafte Persistenz.
- Falls selbst die `workers.dev`-Adresse/DNS-Schicht nicht erreichbar ist, kann dies nicht innerhalb des Workers repariert werden.
- Der Live-Release gilt erst als bestätigt, wenn auch das echte Suchpaket erfolgreich ist.

## Cloudflare Workers Free

Weiterhin dokumentiert: 100.000 Requests pro Tag, 10 ms CPU je HTTP-Request, 128 MB Speicher, 50 Subrequests je Invocation, sechs gleichzeitige ausgehende Verbindungen, 3 MB komprimierte Workergröße, eine Sekunde Startup-Zeit und 256 KB Logs pro Request. Quelle: https://developers.cloudflare.com/workers/platform/limits/
