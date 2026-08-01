# GenericParser

Wiederverwendbare Python-Bibliothek zum zuverlässigen Suchen und Auswerten von Anzeigen auf **Kleinanzeigen**.

GenericParser wird zunächst gezielt für die Einbindung in die Projekte **Evercade** und **SNES-PAL-Sammlung** entwickelt. Beide Projekte sollen denselben Parser verwenden und lediglich ihre eigenen Suchprofile, Preisgrenzen und Ergebnisverarbeitung bereitstellen.

## Festgelegter Umfang

### Im Fokus

- Kleinanzeigen als einzige produktive Quelle
- strukturierte, projektunabhängige Suchprofile
- robuste Extraktion aus Ergebnislisten und bei Bedarf Detailseiten
- Normalisierung von Preis, Datum, Ort und Entfernung
- Erkennung von Gesuchen, Stellenanzeigen, Zubehör, Defekten und Duplikaten
- regelbasiertes Matching und nachvollziehbares Scoring
- SQLite-Persistenz für bekannte Anzeigen, Alerts und Preisänderungen
- kontrolliertes Rate-Limiting, Backoff und Layout-Sanity-Checks
- stabile Bibliotheks-API für Evercade und SNES
- automatisierte Tests anhand der fachlichen Abnahmekriterien

### Bewusst noch nicht enthalten

- eBay
- Vinted
- andere Marktplätze
- verpflichtende LLM- oder Bildanalyse
- eine fest eingebaute Benachrichtigungsart
- projektspezifische Produktlisten

Weitere Quellen werden erst begonnen, wenn die Kleinanzeigen-Implementierung im realen Betrieb zuverlässig funktioniert und die Abnahmetests erfüllt.

## Abgrenzung zu Evercade und SNES

GenericParser kennt keine feste Evercade- oder SNES-Sammlung. Die aufrufenden Projekte liefern zur Laufzeit:

- Suchbegriffe und Schreibvarianten
- Produkt- und Modellmerkmale
- Ausschlussbegriffe
- Preisobergrenzen und optionale Richtwerte
- Standort, Radius und Versandpräferenz
- gewünschte Behandlung von Konvoluten
- Callback oder Adapter für die weitere Verarbeitung eines Treffers

GenericParser liefert normalisierte und bewertete Treffer zurück. Darstellung, Sammlungspflege und Benachrichtigung bleiben Aufgabe des jeweiligen Projekts.

## Ziel-API

```python
from generic_parser import KleinanzeigenParser, SearchProfile

parser = KleinanzeigenParser(storage_path="data/anzeigen.db")
results = parser.search(profile)

for result in results:
    if result.should_alert:
        project.handle_match(result)
```

Die konkrete Parser-Serviceklasse folgt innerhalb von Version 0.1. Die bereits vorhandenen Datenmodelle und Normalisierungsfunktionen bilden ihre stabile Grundlage.

## Geplante Struktur

```text
docs/
  KLEINANZEIGEN_PARSING.md    Fachliche Referenz
  ARCHITECTURE.md             Komponenten und Integrationsgrenzen
  ROADMAP.md                  Schritte bis zur stabilen Kleinanzeigen-Version
src/generic_parser/
  models.py                   Anzeigen- und Suchprofilmodelle
  normalization.py            Text-, Preis-, Datum- und Ortsnormalisierung
  matching.py                 Ausschlüsse und Produkt-Matching
  scoring.py                  Bewertungslogik
  sources/kleinanzeigen.py    Kleinanzeigen-Adapter
  storage.py                  SQLite-Persistenz
  service.py                  Öffentliche Bibliotheks-API
  cli.py                      Test- und Diagnosewerkzeug
tests/                        Unit-, Parser- und Integrationstests
```

## Status

**Version 0.1 in Umsetzung.**

Bereits vorhanden:

- installierbare Python-Paketstruktur
- quellenunabhängige Modelle für Suchprofile, Anzeigen, Preise, Orte und Match-Ergebnisse
- Textnormalisierung einschließlich kompakter Modellnummern
- deutsche Preisnormalisierung einschließlich VB, Tausenderpunkt, Dezimalkomma, Gratis, unbekanntem Preis und verdächtigem 1-Euro-Preis
- Orts- und Entfernungsnormalisierung
- relative Kleinanzeigen-Zeitangaben in `Europe/Berlin`
- 15 erfolgreich ausgeführte Tests

Als Nächstes folgen Konfigurationsserialisierung, Matching-Grundlagen und anschließend der Kleinanzeigen-Listenadapter.
