# GenericParser

Wiederverwendbarer Python-Parser für Kleinanzeigen, entwickelt für die spätere Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Status

**Version 0.2b / Paketversion `0.2.0b1`.**

Der Kleinanzeigen-Ergebnislistenparser und ein browserbasiertes Diagnoseinterface sind implementiert. Du kannst gespeicherte Fixtures, eigenes HTML oder kontrollierte Live-Suchen prüfen. Produkt-Matching, Scoring, SQLite und Hintergrundbetrieb folgen in den nächsten Versionen.

## In 0.2b enthalten

- Keyword- und Kategorie-URLs für Kleinanzeigen
- verifizierbare interne Location-ID und Radiuswirkung
- sequenzieller HTTP-Client mit Delay, Retry und Backoff
- Ergebnislistenparser mit TOP-Deduplizierung und Fehlerisolation
- Unterscheidung von Ergebnissen, Nulltreffer, Blockierung und Layoutänderung
- FastAPI-Diagnoseinterface im Dark Mode
- Live-, Fixture- und HTML-Testmodus
- Anzeige von Such-URLs, Parserdiagnose und normalisierten Anzeigen
- Location-ID-Hilfe und Radiusvergleich
- optionales Speichern von Live-HTML als Fixture
- Docker- und lokale Startoption
- automatisierte Tests einschließlich Web-API

## Webinterface starten

### Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
generic-parser-web
```

Unter Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
generic-parser-web
```

Danach `http://127.0.0.1:8000` im Browser öffnen.

Alternativ stehen `start-interface.sh` und `start-interface.bat` bereit.

### Docker

```bash
docker compose up --build
```

Die Weboberfläche ist anschließend ebenfalls unter `http://127.0.0.1:8000` erreichbar. Gespeicherte Fixtures bleiben im lokalen Verzeichnis `data/fixtures` erhalten.

## Testmodi

### Fixture

Reproduzierbare Paket-Fixtures prüfen:

- normale Ergebnisse mit TOP-Duplikat und Kartenfehler
- Nulltreffer
- Layoutänderung
- Block-/CAPTCHA-Seite

### HTML

Gespeichertes oder kopiertes HTML einer Ergebnisliste direkt einfügen und ohne Netzwerkzugriff parsen.

### Live

Eine echte Kleinanzeigen-Suche starten. Lokale Suchen benötigen gemeinsam:

- fünfstellige PLZ
- interne Kleinanzeigen-Location-ID
- optionalen Radius

Die Oberfläche kann die Location-ID aus einer bereits gefilterten Kleinanzeigen-URL extrahieren und die Radiuswirkung durch einen Vergleich mit einer bundesweiten Suche prüfen.

## CLI bleibt verfügbar

```bash
generic-parser fetch examples/evercade_sunsoft_collection_1.yaml --limit 10
generic-parser parse-fixture tests/fixtures/kleinanzeigen_results.html
generic-parser location-id "https://www.kleinanzeigen.de/s-37136/test/k0l1234r50"
```

## Python-Integration

```python
from generic_parser import GenericParser, KleinanzeigenAdapter, KleinanzeigenHttpClient
from generic_parser import load_profile

profile = load_profile("examples/evercade_sunsoft_collection_1.yaml")

with KleinanzeigenHttpClient() as http:
    listings = GenericParser(KleinanzeigenAdapter(http=http)).search(profile)
```

## Tests

```bash
pytest
```

Der Live-Smoke-Test ist standardmäßig deaktiviert:

```bash
GENERIC_PARSER_LIVE_TEST=1 pytest -m live -q
```

Weitere Hinweise stehen in `docs/TESTING_0_2A.md` und `docs/TESTING_0_2B.md`.
