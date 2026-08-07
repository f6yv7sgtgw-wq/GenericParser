# GenericParser Roadmap

## Fachlicher Referenzkern 0.44.4

0.44.4 bleibt die fachliche Vergleichsbasis für Suchfluss, echte Kleinanzeigen-Weiter-Navigation, Extraktion, Datenkonsistenz und Ampelbewertung ausschließlich aktiver Regeln.

## Stabile Rückfallreferenz 0.44.6.5

0.44.6.5 bleibt der operative Rückfallstand mit 7er-Arbeitspaketen, fünf Sekunden Browserpause, echter Weiter-Navigation, persistentem Fortschritt und bestehendem einmaligem Auto-Resume-Verhalten.

## 0.45.0 – Integrierbares Parsermodul

Abgeschlossen:

- `generic-parser-module-v1`
- projektneutrale Profile, Listings, Pagination und Summary
- Evercade- und SNES-PAL-Adapter
- unveränderte Delegation an den 0.44.4-Suchkern
- Debug und netzwerkfreie Modultests standardmäßig deaktiviert

## 0.45.1 – Infrastrukturstabilisierung

Status: **Release Candidate / Deployment-Abnahme**.

Ziel: dauerhaft zuverlässige Kommunikation zwischen Cloudflare Worker und Browserclients ohne Änderung der Suchlogik.

Enthalten:

- `GET /health`
- `GET /version` und kompatibles `GET /api/version`
- `GET /diagnostics`
- `POST /search`
- `POST /api/search`
- `POST /api/module/search`
- kanonisches `POST /api/module/v1/search`
- globale CORS-Middleware
- browserkompatible `OPTIONS`-Preflights
- einheitliche `Access-Control-Allow-*`-Header
- Request-ID, Timestamp, Route, Methode, Origin, User-Agent, Laufzeit, HTTP-Status und Trefferzahl im Workerlog
- Fehler und Stacktrace im Workerlog
- Syntax-, Metadaten-, Routing-, CORS- und Smoke-Tests vor dem Deploy
- Health-, Versions-, Diagnostics-, CORS- und Live-Paket-Test nach dem Deploy
- vollständige Kompatibilität zu `generic-parser-module-v1`

Nicht Bestandteil: neue Quellen, Multi-Quellen-Suche, Rankingänderungen oder Preisbewertung.

### Abnahmekriterien 0.45.1

1. `/health` meldet `0.45.1` und `gp-0451-20260807-1`.
2. `/version` meldet denselben Build und Vertrag.
3. `/diagnostics` bestätigt Routing, API, Modulvertrag und CORS.
4. `OPTIONS /api/module/search` liefert browserkompatible Preflight-Header.
5. `/api/search` bleibt zur 0.45.0-Suchbasis kompatibel.
6. `/api/module/search` und `/api/module/v1/search` liefern denselben Modulvertrag.
7. Live-Arbeitspakete bleiben auf höchstens sieben Listings begrenzt.
8. Evercade Next kann die Endpunkte aus dem Browser erreichen.
9. Bei Regression bleibt die stabile Rückfallreferenz `0.44.6.5` verfügbar.

## 0.45.2 – Evercade-Integration

- GenericParser 0.45.1 im Evercade-Projekt produktiv anbinden
- Cartridge-Daten in `ModuleSearchProfile` übersetzen
- Richtwert und Maximalpreis übergeben
- Ergebnisse, Ampel, URL, Preis und Zustand zurückführen
- End-to-End-Vergleichsläufe dokumentieren

## 0.45.3 – SNES-PAL-Integration

- GenericParser im SNES-Sammlungsmanager anbinden
- PAL-Titel, Varianten und Ausschlussbegriffe übertragen
- NTSC/Repro-Prüfung projektspezifisch ergänzen
- Ergebnisvertrag gegen reale SNES-Suchprofile testen

## 0.45.4 – Gemeinsame Integrationsabnahme

- identische Modulversion in Evercade und SNES
- Referenzprofile und Fixture-Ergebnisse
- Vertragskompatibilität und Fehlerdarstellung
- gemeinsame Debug- und Testschalter
- dokumentierter Rückfall je Projekt

## 0.46 – Produktklassifizierung

- Hauptprodukt, Zubehör, Ersatzteil, Bundle, Gesuch, Vermietung und Service unterscheiden
- projektspezifische Klassifikationsregeln
- Regressionstests aus Evercade- und SNES-Suchen

## 0.47 – Cartridge-Normalisierung

- Evercade- und SNES-PAL-Titel vereinheitlichen
- Schreibvarianten, Nummern und Editionen normalisieren
- Einzelmodule aus Bundles erkennen

## 0.48 – Projektintegration ausbauen

- Suchprofile pro fehlender Cartridge
- strukturierte Übergabe von Treffer, Ampel und Angebotsdaten
- mehrere Quellen hinter dem gemeinsamen Modulvertrag vorbereiten

## 0.49 – Deal Engine

- Preis gegen Richtwert und Maximalpreis
- Zustand, Vollständigkeit und Versand
- Deal-Klassen und Gesamtpreis

## 0.50 – Serverseitige Suchaufträge

- Queue, Workflow oder Durable Object separat bewerten
- persistente Arbeitspakete statt Browser-Recovery
- nur neue oder geänderte Angebote melden
- Ergebnis- und Preisverlauf
- Benachrichtigungen für Evercade und SNES

## 0.51 – Betrieb und Qualität

- feste Regressionstests
- Referenzsuchen für Evercade und SNES
- Betriebsdiagnose
- Release- und Deployment-Checkliste
