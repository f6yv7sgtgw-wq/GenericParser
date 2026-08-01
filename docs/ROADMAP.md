# Roadmap

## Leitlinie

Kleinanzeigen wird vollständig und belastbar umgesetzt, bevor eine zweite Quelle begonnen wird. Jede Phase muss durch Tests und reale Suchläufe abgesichert sein.

## Version 0.1 – Bibliothekskern ✅

Abgeschlossen.

## Version 0.2a – Kleinanzeigen-Ergebnislisten ✅

Abgeschlossen: URL-Erzeugung, HTTP-Client, Ergebnislistenparser, Diagnosezustände, TOP-Deduplizierung und Fixtures.

## Version 0.2b – Diagnose-Webinterface ✅

Abgeschlossen: manuelle Browsertests, Fixture-/HTML-/Live-Modus und sichtbare Parserdiagnose.

## Version 0.2c – Mobile PWA und Worker-Vorbereitung ✅

- mobile Cloudflare-PWA
- Python-Worker-Einstiegspunkt
- Ein-Seiten- und Trefferbegrenzung
- Demo- und Browser-Dateimodus
- optionaler Zugriffstoken

**Abnahme:** technisch abgeschlossen. Direkte Browserdemo und Worker-Paket sind vorhanden.

## Version 0.2d – Produktives Cloudflare-Deployment 🚧

- Workers-Builds-Erststart
- GitHub-Actions-Deployment
- Cloudflare-Secrets und Produktionsumgebung
- Health- und PWA-Smoke-Test
- Rollback-Prozess
- vollständige öffentliche HTTPS-URL

**Abnahme:** Code und Automatisierung abgeschlossen. Die finale Abnahme erfordert einmalig die Autorisierung des Cloudflare-Kontos und einen echten Live-Deploy.

## Version 0.3 – Matching und Scoring

- Modellnummern- und Schreibvarianten-Matching
- Gesuch-, Stellenanzeigen-, Zubehör- und Defektfilter
- Negationsbehandlung für Begriffe wie „nicht defekt“
- Konvolut-Erkennung als eigene Trefferklasse
- nachvollziehbares Score- und Begründungsmodell
- Feedback im Diagnose-Webinterface

## Version 0.4 – Detailseiten, Persistenz und Worker

- selektives Laden von Detailseiten im Graubereich
- SQLite für gesehene Anzeigen, Alerts und Preisverlauf
- Baseline-Lauf ohne Alert-Flut
- erneute Bewertung bei Preissenkungen
- zentraler Hintergrund-Worker und kleine API

## Version 0.5 – Integration Evercade

## Version 0.6 – Integration SNES

## Version 0.7 – Betriebsstabilität

## Version 1.0 – Kleinanzeigen stabil

Erst nach Version 1.0 wird eine zweite Quelle wie eBay oder Vinted begonnen.
