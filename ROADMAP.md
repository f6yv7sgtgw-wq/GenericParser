# GenericParser Roadmap

## Referenzen

- Fachlicher Suchkern: **0.44.4**
- Tiefe stabile Rückfallreferenz: **0.44.6.5**
- Modulvertrag seit 0.45.0: `generic-parser-module-v1`

## 0.45.0 – Integrierbares Parsermodul

Abgeschlossen: gemeinsamer Modulvertrag, Evercade-/SNES-Adapter, optionale Debugdiagnose und netzwerkfreie Selbsttests. Suchverhalten blieb unverändert.

## 0.45.1 – Infrastrukturstabilisierung

Abgeschlossen: CORS, Diagnose, Request-ID, Logging, API-Aliase, Worker-first-Routing und Deployment-Gates. Die reale Evercade-Diagnose zeigte danach jedoch weiterhin Browser-`Load failed` für sämtliche Workerpfade.

## 0.45.2 – Browser Edge Hotfix

Status: **Release Candidate / Live-Abnahme**.

Ziel: Browser-Erreichbarkeit von der ASGI-/Suchruntime entkoppeln. `/health`, `/version`, `/api/version`, `/diagnostics` und alle `OPTIONS`-Requests werden direkt im Cloudflare-Entrypoint beantwortet. ASGI wird erst für Anwendungstraffic lazy geladen. Bootstrapfehler werden als CORS-fähiges HTTP-503-JSON sichtbar statt als undiagnostizierbarer Netzwerkfehler.

Abnahmekriterien:

1. `/health` meldet `0.45.2` und `gp-0452-20260807-1`.
2. `/version` meldet denselben Build und `generic-parser-module-v1`.
3. `/diagnostics` bestätigt Edge-Runtime, Routing, CORS und Preflight.
4. Browser-OPTIONS für `/api/module/search`, `/api/search` und `/search` sind erfolgreich.
5. CORS bleibt auch auf Such- und Bootstrapfehlerantworten vorhanden.
6. Ein reales Modul-Arbeitspaket funktioniert aus dem Evercade-Origin.
7. Suchservice, Matching, Ranking, Preislogik, Pagination, 7er-Pakete und Recovery bleiben unverändert.

## 0.45.3 – Evercade-End-to-End-Abnahme

- Evercade Next gegen den veröffentlichten GenericParser 0.45.2 prüfen
- 80er-Vollsuche erneut durchführen
- Treffer, Fehler, Request-IDs und Laufzeiten dokumentieren
- 0 Fehler auf Transportebene als Ziel

## 0.45.4 – SNES-PAL-Integration und gemeinsame Abnahme

- identischen Modulvertrag im SNES-Sammlungsmanager verwenden
- PAL-Titel, Varianten und Ausschlussbegriffe übertragen
- gemeinsame Fehlerdarstellung und Debugschalter prüfen

## 0.46 – Produktklassifizierung

Hauptprodukt, Zubehör, Ersatzteil, Bundle, Gesuch, Vermietung und Service unterscheiden; projektspezifische Klassifikationsregeln und Regressionstests ergänzen.

## 0.47 – Cartridge-Normalisierung

Evercade- und SNES-PAL-Titel, Schreibvarianten, Nummern und Editionen normalisieren; Einzelmodule aus Bundles erkennen.

## 0.48 – Projektintegration ausbauen

Suchprofile je fehlender Cartridge, strukturierte Trefferübergabe und Vorbereitung mehrerer Quellen hinter dem gemeinsamen Vertrag.

## 0.49 – Deal Engine

Preis gegen Richtwert/Maximalpreis, Zustand, Vollständigkeit, Versand und Deal-Klassen.

## 0.50 – Serverseitige Suchaufträge

Queue/Durable Object bewerten, persistente Arbeitspakete, Änderungsmeldungen, Preisverlauf und Benachrichtigungen.

## 0.51 – Betrieb und Qualität

Feste Regressionstests, Referenzsuchen, Betriebsdiagnose und Release-/Deployment-Checklisten.
