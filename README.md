# GenericParser

Modularer Python-Parser für Kleinanzeigen-Suchen und später weitere Quellen.

## Ziel

GenericParser durchsucht konfigurierbare Quellen nach Produkten, normalisiert Ergebnisse, filtert Fehlalarme, bewertet Kandidaten und speichert den Verlauf lokal.

Die erste Umsetzung orientiert sich an der bereitgestellten Kleinanzeigen-Spezifikation. Zentrale Anforderungen sind:

- Produkte als strukturierte Suchprofile statt als einzelne Suchstrings
- robuste Preis-, Datums- und Ortsnormalisierung
- Erkennung von Gesuchen, Stellenanzeigen, Zubehör, Defekten und Duplikaten
- gestufte Filterpipeline mit lokalem Scoring
- SQLite-Persistenz für gesehene Inserate, Alerts und Preisänderungen
- Baseline-Lauf ohne Benachrichtigungsflut
- sequenzielle Requests, Rate-Limiting und Backoff
- automatisierte Tests für die beschriebenen Sonderfälle

## Geplante Struktur

```text
docs/                         Fachliche Spezifikationen
src/generic_parser/           Python-Paket
  models.py                   Daten- und Produktmodelle
  normalization.py            Text-, Preis-, Datum- und Ortsnormalisierung
  scoring.py                  Filter- und Bewertungslogik
  sources/                    Quellenspezifische Adapter
  storage.py                  SQLite-Persistenz
  cli.py                      Kommandozeilen-Schnittstelle
tests/                        Automatisierte Tests
```

## Status

Projekt initialisiert. Die fachlichen Pflichtangaben für den ersten produktiven Suchlauf – Ort, Radius, Produkte, Preisgrenzen, Laufzeitumgebung und Benachrichtigungsweg – werden vor der konkreten Implementierung festgelegt.
