# Changelog

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

### Noch nicht enthalten

- Live-Zugriff auf Kleinanzeigen
- Ergebnislisten- und Detailseitenparser
- Matching, Scoring, SQLite und Hintergrundbetrieb
- Webinterface
