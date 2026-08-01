# Changelog

## 0.2.0rc1 – 2026-08-01

Mobile Cloudflare-Worker/PWA-Version für manuelle Kleinanzeigen-Diagnose.

### Neu

- Python-Worker-Einstiegspunkt mit FastAPI und ASGI
- asynchroner Ein-Seiten-Abruf für Cloudflare Workers
- CPU-reduzierter Ergebnisparser mit begrenzter Ausgabe
- mobile PWA mit Home-Bildschirm-Installation und Offline-App-Shell
- Live- und Demo-Modus
- optionale Absicherung über ein Worker-Secret `APP_TOKEN`
- Workers Static Assets, Wrangler-Konfiguration und Deployment-Anleitung
- automatisierte Worker-API- und PWA-Asset-Tests

### Grenzen

- keine Hintergrundläufe oder Persistenz
- eine Ergebnisseite und maximal 20 Anzeigen pro Anfrage
- echte Cloudflare-CPU-Zeit und Kleinanzeigen-Erreichbarkeit müssen nach dem ersten Deployment gemessen werden

## 0.2.0b1 – 2026-08-01

Diagnose-Webinterface für manuelle und reproduzierbare Parserprüfungen.

### Neu

- FastAPI-Weboberfläche im Dark Mode
- Live-, Fixture- und HTML-Testmodus
- Anzeige generierter Such-URLs und vollständiger Seitendiagnose
- normalisierte Ergebnisdarstellung mit Bildern, Preisen, Orten, Zeitstempeln und Tags
- Location-ID-Extraktion aus einer Kleinanzeigen-URL
- Radiusvergleich zwischen lokaler und bundesweiter Suche
- optionales Speichern abgerufener HTML-Seiten als Fixture
- serialisierte Live-Suchen gegen parallele Abruflast
- Dockerfile, Docker Compose und Startskripte
- HTTP- und Browseroberflächen-Tests

### Weiterhin nicht enthalten

- Produkt-Matching und Scoring
- Detailseitenparser
- SQLite, Hintergrund-Worker und Benachrichtigungen

## 0.2.0a1 – 2026-08-01

Erster Kleinanzeigen-Ergebnislistenadapter.

### Enthalten

- Keyword- und Kategorie-URLs
- interne Location-ID und Radiusprüfung
- kontrollierter HTTP-Client mit Delay, Retry und Backoff
- Ergebnislistenparser, TOP-Deduplizierung und Kartendiagnose
- Erkennung von Nulltreffer, Blockierung und Layoutänderung
- CLI und reproduzierbare HTML-Fixtures

## 0.1.0 – 2026-08-01

Erster abgeschlossener Bibliothekskern mit Datenmodellen, Normalisierung, Konfiguration, Serviceklasse und Beispielprofilen.
