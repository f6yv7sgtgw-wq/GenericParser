# GenericParser

Wiederverwendbare Python-Bibliothek zum zuverlässigen Suchen und Auswerten von Anzeigen auf **Kleinanzeigen**.

GenericParser wird zunächst für die Einbindung in die Projekte **Evercade** und **SNES-PAL-Sammlung** entwickelt. Beide Projekte verwenden denselben Parserkern und liefern nur ihre eigenen Suchprofile, Preisgrenzen und Ergebnisverarbeitung.

## Status

**Version 0.1.0 abgeschlossen.**

Der Bibliothekskern ist installierbar, konfigurierbar und getestet. Live-Zugriffe auf Kleinanzeigen beginnen mit Version 0.2.

## Enthalten in 0.1

- Datenmodelle für `SearchProfile`, `Listing` und `MatchResult`
- Normalisierung von Text, Preis, Ort und Datum
- JSON- und YAML-Konfiguration
- öffentliche Serviceklasse mit austauschbarem Quellenadapter
- Beispielprofile für Evercade und SNES PAL
- automatisierte Tests

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Unter Windows wird die virtuelle Umgebung mit `.venv\Scripts\activate` aktiviert.

## Suchprofil laden

```python
from generic_parser import load_profile

profile = load_profile("examples/evercade_sunsoft_collection_1.yaml")
print(profile.display_name)
```

## Service verwenden

Version 0.1 definiert bereits die stabile Einbindungsrichtung. Ein Quellenadapter liefert `Listing`-Objekte; `GenericParser` stellt sie dem aufrufenden Projekt bereit.

```python
from generic_parser import GenericParser, SearchProfile

parser = GenericParser(source=my_source_adapter)
listings = parser.search(profile)
```

Der echte Kleinanzeigen-Adapter folgt in Version 0.2.

## Projektgrenzen

GenericParser übernimmt künftig:

- Such-URL-Erzeugung
- Kleinanzeigen-Abruf und Parsing
- Normalisierung
- Matching und Scoring
- technische Persistenz und Deduplizierung

Evercade und SNES übernehmen:

- Produktkataloge und Sammlungsstatus
- Preislimits und Richtwerte
- Darstellung und Benachrichtigung
- Nutzerfeedback

## Dokumentation

- [`docs/KLEINANZEIGEN_PARSING.md`](docs/KLEINANZEIGEN_PARSING.md) – fachliche Referenz
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – Architektur und Integrationsgrenzen
- [`docs/ROADMAP.md`](docs/ROADMAP.md) – weitere Versionen
- [`CHANGELOG.md`](CHANGELOG.md) – Versionshistorie
