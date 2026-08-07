# GenericParser 0.45.1 – API, Infrastruktur und Grenzen

Build: `gp-0451-20260807-1`  
Modulvertrag: `generic-parser-module-v1`

## Zweck

0.45.1 ist ein reines Stabilitäts- und Infrastruktur-Release. Suchalgorithmus, Matching, Ranking, Preisbewertung, Pagination und 7er-Arbeitspakete bleiben unverändert. Die Suchimplementierung bleibt `search_service_v0450` auf der stabilen Referenz 0.44.6.5 / Suchkern 0.44.4.

## Browser- und Diagnose-Endpunkte

- `GET /health` – Health, Build, Vertrag und CORS-Status.
- `GET /version` – kanonische Worker-Identität.
- `GET /api/version` – kompatibler Versionsalias.
- `GET /diagnostics` – Routing, API, Modulvertrag, CORS, Preflight und Referenzstatus.

## Such-Endpunkte

- `POST /search` – Alias der kompatiblen Legacy-Suche.
- `POST /api/search` – bestehender Legacy-/UI-Vertrag.
- `POST /api/module/search` – browserfreundlicher Alias der Modul-v1-Seitensuche.
- `POST /api/module/v1/search` – kanonischer Modul-v1-Endpunkt.
- `POST /api/module/v1/profile/validate`
- `GET /api/module/v1/capabilities`
- `GET /api/module/v1/self-test?enabled=true`

Der Vertrag `generic-parser-module-v1` bleibt vollständig kompatibel für **Evercade** und **SNES**.

## CORS

Jede Worker-Antwort erhält konsistente `Access-Control-Allow-*`-Header. `OPTIONS` wird global beantwortet. Freigegeben sind `GET`, `POST` und `OPTIONS`; notwendige Content-, Contract-, Token-, Debug-, Test- und Request-ID-Header sind im Preflight erlaubt. Der Worker exponiert Build-, Contract- und Request-ID-Header für Browserdiagnosen.

## Request-Logging

Pro Request werden serverseitig protokolliert: Request-ID, Timestamp, Route, Methode, Origin, User-Agent, Laufzeit, HTTP-Status, Trefferzahl sowie Fehler und Stacktrace. Stacktraces werden geloggt, aber nicht ungefiltert an Browserclients ausgeliefert.

## Einheitliche Fehler- und Diagnosefelder

Diagnose- und Fehlerantworten enthalten mindestens Status/Detail, `request_id`, `timestamp` und Build-/Contract-Header. Bestehende Suchantworten werden nicht in ein neues Envelope gezwungen, damit die Modul- und Legacy-Verträge kompatibel bleiben.

## Deploymentprüfung

Vor Deployment laufen Release-Metadatencheck, Regressionstests, Syntaxchecks und Routing-/CORS-Tests. Nach Deployment prüft `scripts/check_deployment.py` Health, Version, Diagnostics, Preflight, Browser-Assets und ein echtes auf sieben Treffer begrenztes Modul-Arbeitspaket.

## Cloudflare Workers Free

Das Release bleibt für den Cloudflare Workers Free Tarif ausgelegt. Maßgeblich sind die jeweils aktuellen offiziellen Limits: https://developers.cloudflare.com/workers/platform/limits/

Der Release-Stichtag dokumentiert weiterhin 100.000 Requests/Tag, 10 ms CPU-Zeit je HTTP-Request, 128 MB Speicher je Isolat, 50 Subrequests je Invocation und sechs gleichzeitige ausgehende Verbindungen. Diese Grenzen sind Infrastrukturgrenzen und keine Vollständigkeitsgarantie für sehr lange Kleinanzeigen-Suchen.

## Bekannte Grenzen

- Nur Kleinanzeigen ist als automatische Suchquelle implementiert.
- Keine Multi-Quellen-Suche in 0.45.1.
- Keine Ranking- oder Preisbewertungsänderung.
- Lange Suchläufe bleiben browserkoordiniert; es gibt keine dauerhafte serverseitige Queue.
- CORS kann Worker-/Browser-Kommunikation stabilisieren, aber externe Kleinanzeigen-/Cloudflare-Fehler nicht verhindern.
- Request-Logging unterliegt den Cloudflare-Loglimits.
- `Access-Control-Allow-Origin: *` wird ohne Credential-Cookies verwendet; optionale API-Token laufen über Header.

## Kompatibilität

Evercade Next und SNES PAL Sammlung können weiterhin `generic-parser-module-v1` nutzen. Neue Clients sollen bevorzugt `/api/module/search` oder den kanonischen `/api/module/v1/search` verwenden. Bestehende Clients auf `/api/search` bleiben unterstützt.
