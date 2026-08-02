# Changelog

Die Einträge fassen die produktiven Entwicklungsstände zusammen. Einzelne Versionen bestehen aus mehreren technischen Commits; der Abschluss-Commit steht in `docs/RELEASE_INDEX.md`.

## 0.42.3 – 2026-08-02

- Pagination beendet die Suche, sobald `reported_total` erreicht ist.
- Kurze HTML-Ergebnisseiten werden als Abschluss erkannt.
- Unnötige Folgeseiten und dadurch ausgelöste 503/1101-Ketten werden vermieden.
- UI, Controller, Handshake, Worker, Eventlog und PWA-Cache auf `0.42.3` / `gp-0423-20260802-1` vereinheitlicht.
- Technischer Abschluss-Commit: `9c8841fecac53ffaa127a7ed83ca94492a260a88`.

## 0.42.2 – 2026-08-02

- Suchlogik aus älteren FastAPI-Worker-Apps herausgelöst.
- App-freier Ein-Seiten-Search-Service eingeführt.
- Nur der 0.42.2-Bootstrap besitzt Routen und Middleware.
- Konsistenzprüfung für abgerufene, sichtbare und ausgeblendete Treffer ergänzt.
- UI, Controller, Handshake, Worker, Eventlog und PWA-Cache vereinheitlicht.

## 0.42.1 – 2026-08-02

- Suchbutton nach erfolgreichem Handshake zuverlässig aktiviert.
- Zentraler UI-Zustand für Booting, Idle und Blocked.
- Eventlog um Button- und Zustandswechsel erweitert.

## 0.42.0 – 2026-08-02

- Minimaler Lazy-Bootstrap eingeführt.
- Versions- und Readiness-Endpunkte ohne Parserimporte.
- Suchmodule erst innerhalb von `/api/search` geladen.
- Strukturierte Import- und Suchphasen ergänzt.

## 0.41.1 – 2026-08-02

- Deployment-Handshake zwischen UI und Worker eingeführt.
- Einheitliche Version, Build-ID und API-Vertrag über Header und JSON.
- Live-Suche bei inkonsistentem Deployment gesperrt.
- Instabile Ressourcen-Middleware aus dem produktiven Pfad entfernt.

## 0.41.0 – 2026-08-02

- Ressourcenmessungen pro Seite ergänzt.
- Gesamt-, CPU-, Fetch- und Parsezeiten protokolliert.
- Antwortgrößen und Kartenanzahl dokumentiert.

## 0.40.9 – 2026-08-02

- HTML-Fallback in serverseitige Diagnosephasen aufgeteilt.
- UI-Überlappungen und lange Eventlog-Zeilen korrigiert.
- Synthetische Fehlerantworten versionskonsistent gemacht.

## 0.40.8 – 2026-08-02

- Seitennummer, Request-ID, Payload, Fetch-/Parse-Marker und Antwortgrößen ins Eventlog aufgenommen.

## 0.40.7 – 2026-08-02

- Overlay-Controller entfernt.
- Start, Stopp, Fortsetzen und Cooldown in einen Controller zusammengeführt.
- Eventlog gedrosselt.

## 0.40.6 – 2026-08-02

- Sanfter Suchstopp eingeführt.
- Eigene Eventlog-Unterseite ergänzt.

## 0.40.5 – 2026-08-02

- Diagnosephasen, Ray-ID und Laufzeitinformationen für Workerfehler ergänzt.

## 0.40.4 – 2026-08-02

- Cloudflare-1101-Erkennung ohne automatische Retry-Schleife.
- Worker-Pfad auf stabileren Seitenworker zurückgeführt.

## 0.40.3 – 2026-08-02

- Integrierte Session-Steuerung für Start, Stopp und Folgesuchen.
- Alte Requests und Retries von neuen Suchsessions getrennt.

## 0.40.2 und frühere 0.3x/0.4x-Zwischenstände

- Aufbau der seitenweisen Suche, Pagination, Deduplizierung, Fortsetzung, Workerstatus und mobilen PWA.
- Die vollständigen Einzeländerungen bleiben über die Git-Historie nachvollziehbar.

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

## 0.2.0rc1 – 2026-08-01

Mobile Cloudflare-Worker/PWA-Version für manuelle Kleinanzeigen-Diagnose.

## 0.2.0b1 – 2026-08-01

Diagnose-Webinterface für manuelle und reproduzierbare Parserprüfungen.

## 0.2.0a1 – 2026-08-01

Erster Kleinanzeigen-Ergebnislistenadapter.

## 0.1.0 – 2026-08-01

Erster abgeschlossener Bibliothekskern mit Datenmodellen, Normalisierung, Konfiguration, Serviceklasse und Beispielprofilen.
