# Roadmap

## Leitlinie

Kleinanzeigen wird vollständig und belastbar umgesetzt, bevor eine zweite Quelle begonnen wird. Jede Phase muss durch Tests und reale Suchläufe abgesichert sein.

## Version 0.1 – Bibliothekskern ✅

- Python-Paketstruktur
- Datenmodelle für SearchProfile, Listing und MatchResult
- JSON- und YAML-Konfigurationsschema
- Text-, Preis-, Datums- und Ortsnormalisierung
- öffentliche Service-Schnittstelle
- Unit-Tests für Normalisierungs- und Konfigurationsfälle
- Beispielprofile für Evercade und SNES

**Abnahme:** abgeschlossen. Modelle, Konfiguration und Normalisierung funktionieren unabhängig von einem Live-Zugriff auf Kleinanzeigen.

## Version 0.2a – Kleinanzeigen-Ergebnislisten ✅

- URL-Erzeugung für Keyword- und Kategoriesuche
- Location-ID-Verwaltung und Verifikation
- sequenzieller HTTP-Client
- Parsing der Ergebniskarten
- Erkennung von Nulltreffer, Layoutwechsel und Blockierung
- Deduplizierung doppelter TOP-Anzeigen
- gespeicherte HTML-Fixtures für reproduzierbare Tests

**Abnahme:** Implementierung und Fixture-Abnahme abgeschlossen. Der optionale Live-Smoke-Test ist vorhanden und wird in einer Umgebung mit externem Netzwerkzugriff ausgeführt.

## Version 0.2b – Diagnose-Webinterface ✅

- manuelle Testsuchen im Browser
- Anzeige von Such-URL, Location-ID, Rohdaten und normalisierten Feldern
- Diagnose von Nulltreffern, Blockierung und Selektorfehlern
- Speicherung geeigneter HTML-Fixtures für Tests

**Abnahme:** abgeschlossen. Der Parser kann im Browser per Fixture, eingefügtem HTML oder Live-Suche geprüft werden; Diagnosezustände und normalisierte Listings werden sichtbar dargestellt.

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
- kontrollierte Retries, Backoff und Rate-Limiting
- zentraler Hintergrund-Worker und kleine API

## Version 0.5 – Integration Evercade

- Adapter im Evercade-Projekt
- Suchprofile aus fehlenden oder überwachten Cartridges
- Übergabe von Preislimits und Richtwerten
- realer Parallelbetrieb mit Feedback zu Fehlalarmen

## Version 0.6 – Integration SNES

- Adapter im SNES-PAL-Sammlung-Projekt
- Suchprofile für SNES-PAL-Titel und Schreibvarianten
- Nutzung derselben Bibliotheks-API
- Beseitigung verbleibender projektspezifischer Annahmen

## Version 0.7 – Betriebsstabilität

- längerer Realbetrieb
- Parser-Metriken und Diagnoseausgaben
- Wartungsalarm bei Layoutänderung
- Kalibrierung von Scores und Schwellenwerten
- dokumentierter Umgang mit Blockierungen

## Version 1.0 – Kleinanzeigen stabil

- dokumentierte öffentliche API
- Migrations- und Integrationsanleitung
- vollständige Testsuite
- reproduzierbare Releases
- beide Zielprojekte produktiv angebunden
- offene bekannte Einschränkungen dokumentiert

## Nach Version 1.0

Erst dann wird anhand der Erfahrungen entschieden, ob eBay, Vinted oder eine andere Plattform als nächste Quelle sinnvoll ist.
