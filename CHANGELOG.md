# Changelog

## 0.2.0a1 – 2026-08-01

Kleinanzeigen-Ergebnislistenadapter für Meilenstein 0.2a.

### Enthalten

- URL-Erzeugung für Keyword- und Kategoriesuchen
- explizite Kleinanzeigen-Location-ID und Hilfsfunktion zur Extraktion aus Such-URLs
- Prüfung der Radiuswirkung durch lokalen/bundesweiten Kartenvergleich
- sequenzieller HTTP-Client mit Browser-Headern und Request-Delay
- begrenzte Retries sowie exponentieller Backoff bei 403/429 und 5xx
- Parser für Ergebnislisten mit Preis-, Ort- und Datumsnormalisierung
- Beschreibung, Tags und Vorschaubild als optionale Listing-Felder
- Deduplizierung doppelter TOP-Anzeigen innerhalb und über mehrere Queries
- Diagnose von Nulltreffer, Blockierung, Layoutänderung und einzelnen Kartenfehlern
- CLI für Live-Suche, HTML-Fixtures und Location-ID-Prüfung
- reproduzierbare HTML-Fixtures, Mock-HTTP-Tests und optionaler Live-Smoke-Test

### Noch nicht enthalten

- Produkt-Matching und Scoring
- selektive Detailseitenabrufe
- SQLite, Preisverlauf und Hintergrund-Worker
- Diagnose-Webinterface

## 0.1.0 – 2026-08-01

Erster abgeschlossener Bibliothekskern.

### Enthalten

- quellenunabhängige Datenmodelle für Suchprofile, Anzeigen und Match-Ergebnisse
- Normalisierung deutscher Preise, Orte und Kleinanzeigen-Zeitangaben
- Textnormalisierung für Produkt- und Modellvarianten
- JSON- und YAML-Konfiguration mit Validierung und Roundtrip-Unterstützung
- öffentliche Serviceklasse mit austauschbarem Quellenadapter
- Beispielprofile für Evercade und SNES PAL
- automatisierte Tests für Modelle, Konfiguration, Service und Normalisierung
