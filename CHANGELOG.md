# Changelog

Die Einträge fassen die produktiven Entwicklungsstände zusammen. Einzelne Versionen bestehen aus mehreren technischen Commits; der Abschluss-Commit steht in `docs/RELEASE_INDEX.md`.

## 0.44.6.2 – 2026-08-04

- Einmalige automatische Fortsetzung nach einer terminalen 503/1101-Fehlerkette ergänzt.
- Trigger nur bei `search_end` mit `retry_exhausted` und bestätigtem Cloudflare 1101 oder mindestens zwei unterschiedlichen HTML-503-Requests.
- 90 Sekunden Ruhezeit vor der ersten Worker-Bereitschaftsprüfung.
- Bis zu vier `/api/version`-Prüfungen im Abstand von 15 Sekunden.
- Fortsetzung verwendet den bereits vorhandenen persistenten Suchstand und die bestehende Resume-Funktion.
- Höchstens ein automatischer Resume je Suchkette; danach bleibt nur manuelles Fortsetzen.
- Manuelles Fortsetzen überschreibt eine wartende Automatik.
- Eventlog um Planung, Health-Checks, Start, laufende Session, Abschluss und manuellen Fallback ergänzt.
- Suchkern, Pagination, Extraktion, Ampellogik, 7er-Pakete und 5-Sekunden-Pause bleiben unverändert auf Referenz 0.44.4.
- Live-Test erforderlich; eine frische Cloudflare-Worker-Instanz wird nicht garantiert.

## 0.44.6.1 – 2026-08-04

- Falsche Versionsabweichung im Referenzmodus beseitigt.
- Versionsprüfung auf Version, Build und API-Vertrag begrenzt.
- Fehlendes erweitertes Diagnoseschema korrekt als optional dargestellt.
- HTML-503 verständlich als temporärer Abruffehler eingeordnet.
- Live-Test: neun erfolgreiche Arbeitspakete, 60 gespeicherte Ergebnisse, danach 503 und Cloudflare 1101 vor ASGI.
- Suchstand und manuelles Fortsetzen blieben verfügbar.

## 0.44.6 – 2026-08-04

- Funktionaler Rückbau auf den vollständigen 0.44.4-Referenzkern.
- Experimentelle Parser- und Cursorlogik aus 0.44.5.x nicht mehr verwendet.
- Live-Test: 184 eindeutige Ergebnisse und mindestens 29 erfolgreiche Arbeitspakete.
- Preise, Bilder, Ampel und echte Weiter-Navigation wiederhergestellt.

## 0.44.5 bis 0.44.5.2 – 2026-08-04

- Direkten Standardbibliothek-Worker als Free-Tarif-Experiment umgesetzt.
- Import-/ASGI-Fehler in kurzen Läufen reduziert.
- Funktionale Abdeckung der Referenz jedoch nicht erreicht; Linie als Experiment verworfen.

## 0.44.4 – 2026-08-03

- Ampelbewertung auf tatsächlich gesetzte Felder und aktive Optionen begrenzt.
- Leere Pflicht-, Ausschluss-, Modell-, Marken- und Preisfelder werden ignoriert.
- Funktionale Referenz für Suchfluss, Pagination, Extraktion und Ampel.

## 0.42.7 – 2026-08-03

- Cloudflare-Trace als eindeutige Ursache ausgewertet: `Worker exceeded CPU time limit`.
- Free-Tarif-Pfad vollständig auf kleine virtuelle Arbeitspakete umgestellt.
- Eine Kleinanzeigen-Quellseite wird in bis zu vier Pakete mit höchstens sieben Karten zerlegt.
- Vollständige BeautifulSoup-DOM-Rekonstruktion und schweres Legacy-Scoring aus dem produktiven Free-Pfad entfernt.
- Browser wartet fünf Sekunden zwischen den Paketen und speichert nach jedem Paket den Suchstand.
- Gemeinsame Identität `0.42.7` / `gp-0427-20260803-1` / `match-v6.1-page-worker` für Worker, UI, Controller, Handshake, Eventlog und Cache.
- Technischer Abschluss-Commit: `119a05985d11017940b775bb2c6cc7bc6acd992a`.

## 0.42.6 – 2026-08-02

- Experimentellen FFI-Transport zurückgenommen.
- Eigenständigen minimalen Readiness-Bootstrap eingeführt.
- `/api/version` von Search-Service-Importen entkoppelt.
- Cloudflare-Observability zur Diagnose des tatsächlichen Laufzeitfehlers genutzt.

## 0.42.5 – 2026-08-02

- Experimenteller Workers-Fetch über Python-JavaScript-FFI.
- Die Änderung erwies sich im Live-Betrieb als Regression und wurde in 0.42.6 entfernt.

## 0.42.4 – 2026-08-02

- Gemeinsame Build-Identität für Suchseite, Controller, Handshake, Worker und Eventlog eingeführt.
- Das Eventlog prüft seine Version und Build-ID beim Öffnen gegen `/api/version`.
- Das Eventlog verwendet einen eigenen 0.42.4-Speicherschlüssel und kann nicht mehr unbemerkt alte 0.42.2-Einträge anzeigen.
- Eventlog-Link, Assets und Service-Worker-Cache mit `v=0.424` cachegebustet.
- Produktionsstand: `0.42.4` / `gp-0424-20260802-1` / `match-v6.1-page-worker`.

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

## 0.2.0rc1 – 2026-08-01

Mobile Cloudflare-Worker/PWA-Version für manuelle Kleinanzeigen-Diagnose.

## 0.2.0b1 – 2026-08-01

Diagnose-Webinterface für manuelle und reproduzierbare Parserprüfungen.

## 0.2.0a1 – 2026-08-01

Erster Kleinanzeigen-Ergebnislistenadapter.

## 0.1.0 – 2026-08-01

Erster abgeschlossener Bibliothekskern mit Datenmodellen, Normalisierung, Konfiguration, Serviceklasse und Beispielprofilen.
