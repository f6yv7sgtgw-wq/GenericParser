# Changelog

## 0.2.0rc2 – 2026-08-01

Produktionsreifes Cloudflare-Deployment für Meilenstein 0.2d.

### Neu

- GitHub-Actions-Pipeline für Test und Deployment
- Cloudflare Account-ID und API-Token ausschließlich als Secrets
- optionaler Produktions-Smoke-Test gegen die Worker-URL
- Health-, Startseiten- und PWA-Manifest-Prüfung
- dokumentierter Workers-Builds-Erststart
- Rollback-Skript für letzte oder gezielte Worker-Version
- Produktions-Environment und Schutz gegen parallele Deployments

### Weiterhin nicht enthalten

- Produkt-Matching und Scoring
- automatische Hintergrundläufe
- Persistenz und Benachrichtigungen

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

## 0.2.0b1 – 2026-08-01

Diagnose-Webinterface für manuelle und reproduzierbare Parserprüfungen.

## 0.2.0a1 – 2026-08-01

Erster Kleinanzeigen-Ergebnislistenadapter.

## 0.1.0 – 2026-08-01

Erster abgeschlossener Bibliothekskern mit Datenmodellen, Normalisierung, Konfiguration, Serviceklasse und Beispielprofilen.
