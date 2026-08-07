# Changelog

Die Einträge fassen die produktiven Entwicklungsstände zusammen. Technische Abschlussstände und historische Referenzen stehen zusätzlich in `docs/RELEASE_INDEX.md` und der Git-Historie.

## 0.45.1 – 2026-08-07 – Infrastrukturstabilisierung

- `generic-parser-module-v1` unverändert beibehalten.
- Globale CORS-Behandlung für Browserclients ergänzt.
- `OPTIONS`-Preflight zentral unterstützt.
- Einheitliche `Access-Control-Allow-*`- und Expose-Header ergänzt.
- `GET /health`, `GET /version` und `GET /diagnostics` ergänzt.
- `POST /search` als kompatiblen Alias für `/api/search` ergänzt.
- `POST /api/module/search` als browserfreundlichen Alias für `/api/module/v1/search` ergänzt.
- Request-ID für jeden Request ergänzt und über `X-Request-ID` exponiert.
- Strukturiertes Workerlogging mit Timestamp, Route, Methode, Origin, User-Agent, Laufzeit, HTTP-Status und Trefferzahl ergänzt.
- Fehler und Stacktraces serverseitig protokolliert, ohne ungefilterte Stacktraces an Browserclients auszuliefern.
- Browser-Buildidentität auf `0.45.1` / `gp-0451-20260807-1` aktualisiert.
- PWA-Cache auf den 0.45.1-Stand aktualisiert.
- Deploymentprüfung auf Health, Version, Diagnostics, CORS/Preflight, Browserassets und ein echtes 7er-Live-Arbeitspaket erweitert.
- Evercade Next und SNES bleiben vollständig kompatibel zum bestehenden Modulvertrag.
- Suchalgorithmus, Kleinanzeigen-Quelle, Matching, Ranking, Preisbewertung, Pagination, 7er-Arbeitspakete und Recovery bleiben unverändert auf der 0.45.0-/0.44.6.5-Basis.

## 0.45.0 – 2026-08-05 – Modulversion

- Stabilen Vertrag `generic-parser-module-v1` eingeführt.
- Projektneutrale Profile, Listings, Pagination und Summary ergänzt.
- Evercade- und SNES-PAL-Profiladapter ergänzt.
- Bestehenden `/api/search`-Pfad und den 0.44.4-Suchkern funktional unverändert aus 0.44.6.5 übernommen.
- Debug-Logs und netzwerkfreie Modul-Selbsttests standardmäßig deaktiviert integriert.
- Versionsgebundene API-, Release- und Deploymentdokumentation sowie maschinenlesbare Release-Prüfung eingeführt.

## Historische Referenzlinie 0.44.x

- **0.44.6.5** ist die stabile Rückfallreferenz.
- **0.44.4** ist der fachliche Suchkern für Suche, Pagination, Extraktion und Ampellogik.
- Die Recovery-/Cooldown-Experimente 0.44.6.3 bis 0.44.6.6.1 bleiben verworfen und sind nicht Bestandteil des aktiven 0.45.x-Suchpfads.
- Detaillierte historische Commits und Build-IDs stehen in `docs/RELEASE_INDEX.md` und der Git-Historie.
