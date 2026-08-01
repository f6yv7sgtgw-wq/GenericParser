# GenericParser

Wiederverwendbare Python-Bibliothek zum zuverlässigen Suchen und Auswerten von Anzeigen auf **Kleinanzeigen**.

GenericParser wird zunächst für die Einbindung in die Projekte **Evercade** und **SNES-PAL-Sammlung** entwickelt. Beide Projekte verwenden denselben Parserkern und liefern nur ihre eigenen Suchprofile, Preisgrenzen und Ergebnisverarbeitung.

## Status

**Version 0.2a / Paketversion 0.2.0a1.**

Der Kleinanzeigen-Ergebnislistenadapter, ein kontrollierter HTTP-Client, Diagnosezustände und eine CLI sind implementiert. Das Diagnose-Webinterface folgt in 0.2b.

## Enthalten

- Datenmodelle für `SearchProfile`, `Listing` und `MatchResult`
- JSON- und YAML-Konfiguration
- Keyword- und Kategorie-URLs für Kleinanzeigen
- explizite interne `location_id` statt fehlerhafter PLZ-Nutzung
- sequenzieller HTTP-Client mit Browser-Headern, Delay, Retry und Backoff
- Ergebnislistenparser für Anzeigen-ID, Titel, Link, Preis, Ort, Datum, Beschreibung, Tags und Vorschaubild
- Deduplizierung doppelter TOP-Anzeigen
- Unterscheidung zwischen Nulltreffer, Blockierung und Layoutänderung
- Fehlerisolation pro Ergebniskarte
- CLI für Live-Suche, Fixture-Parsing und Location-ID-Diagnose
- gespeicherte HTML-Fixtures und optionale Live-Smoke-Tests

Noch nicht enthalten sind Produkt-Matching und Scoring, Detailseiten, SQLite und Hintergrundbetrieb.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Unter Windows wird die virtuelle Umgebung mit `.venv\Scripts\activate` aktiviert.

## Echte Suche über die CLI

```bash
generic-parser fetch examples/snes_zelda_link_to_the_past.json --limit 20
```

JSON-Ausgabe:

```bash
generic-parser fetch examples/evercade_sunsoft_collection_1.yaml --json
```

## Fixture prüfen

```bash
generic-parser parse-fixture tests/fixtures/kleinanzeigen_results.html
```

## Location-ID aus einer Browser-URL lesen

```bash
generic-parser location-id "https://www.kleinanzeigen.de/s-.../k0l1234r50"
```

Für lokale Keyword-Suchen werden sowohl `postal_code` als auch die verifizierte
`location_id` benötigt. Die PLZ wird niemals still als interne ID verwendet.

## Eingebettete Nutzung

```python
from generic_parser import GenericParser, KleinanzeigenAdapter, KleinanzeigenHttpClient
from generic_parser import load_profile

profile = load_profile("examples/evercade_sunsoft_collection_1.yaml")

with KleinanzeigenHttpClient() as http:
    adapter = KleinanzeigenAdapter(http=http)
    listings = GenericParser(adapter).search(profile)

for listing in listings:
    print(listing.title, listing.price.amount, listing.url)
```

## Testen

```bash
pytest
```

Optionaler Live-Smoke-Test:

```bash
GENERIC_PARSER_LIVE_TEST=1 pytest -m live -q
```

Weitere Hinweise: [`docs/TESTING_0_2A.md`](docs/TESTING_0_2A.md).

## Projektgrenzen

GenericParser übernimmt:

- Such-URL-Erzeugung
- Kleinanzeigen-Abruf und Ergebnislistenparsing
- Normalisierung und technische Diagnosen
- später Matching, Scoring und Persistenz

Evercade und SNES übernehmen:

- Produktkataloge und Sammlungsstatus
- Preislimits und Richtwerte
- Darstellung und Benachrichtigung
- Nutzerfeedback

## Dokumentation

- [`docs/KLEINANZEIGEN_PARSING.md`](docs/KLEINANZEIGEN_PARSING.md) – fachliche Referenz
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – Architektur und Integrationsgrenzen
- [`docs/ROADMAP.md`](docs/ROADMAP.md) – weitere Versionen
- [`docs/TESTING_0_2A.md`](docs/TESTING_0_2A.md) – Testanleitung
- [`CHANGELOG.md`](CHANGELOG.md) – Versionshistorie
