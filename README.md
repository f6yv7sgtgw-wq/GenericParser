# GenericParser

Wiederverwendbarer Python-Parser für Kleinanzeigen, entwickelt für die spätere Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Status

**Version 0.2c / Paketversion `0.2.0rc1`.**

Zusätzlich zum lokalen Diagnoseinterface enthält das Projekt jetzt eine mobile PWA für Cloudflare Workers. Die Oberfläche läuft auf iPhone und Android im Browser oder vom Home-Bildschirm; der Worker ruft pro manueller Suche genau eine Kleinanzeigen-Ergebnisliste ab.

## In 0.2c enthalten

- alle Funktionen aus 0.2a und 0.2b
- FastAPI-Einstiegspunkt für Python Workers
- asynchroner Cloud-Abruf über `httpx`
- CPU-reduzierter Kartenparser mit `SoupStrainer`
- maximal eine Ergebnisseite und 20 Anzeigen pro Worker-Anfrage
- mobile PWA mit Offline-App-Shell
- Installationsunterstützung für den Home-Bildschirm
- Demo-Modus ohne Kleinanzeigen-Zugriff
- optionale Absicherung über `APP_TOKEN`
- Workers Static Assets und `wrangler.jsonc`
- automatisierte Worker-API- und PWA-Tests

Noch nicht enthalten sind Produkt-Matching, Scoring, Persistenz, automatische Hintergrundläufe und Benachrichtigungen.

## Cloud-Version lokal testen

```bash
uv run --group cloudflare pywrangler dev
```

## Auf Cloudflare veröffentlichen

```bash
uv run --group cloudflare pywrangler login
uv run --group cloudflare pywrangler deploy
```

Optionaler Zugriffsschutz:

```bash
uv run --group cloudflare pywrangler secret put APP_TOKEN
```

Die veröffentlichte `workers.dev`-URL kann auf dem Smartphone zum Home-Bildschirm hinzugefügt werden. Details stehen in [`cloudflare/README.md`](cloudflare/README.md) und [`docs/TESTING_0_2C.md`](docs/TESTING_0_2C.md).

## Lokales Webinterface

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
generic-parser-web
```

Danach `http://127.0.0.1:8000` öffnen. Alternativ stehen Docker, `start-interface.sh` und `start-interface.bat` bereit.

## CLI

```bash
generic-parser fetch examples/evercade_sunsoft_collection_1.yaml --limit 10
generic-parser parse-fixture tests/fixtures/kleinanzeigen_results.html
generic-parser location-id "https://www.kleinanzeigen.de/s-37136/test/k0l1234r50"
```

## Tests

```bash
python -m pytest -q
```

Der echte Live-Smoke-Test ist standardmäßig deaktiviert:

```bash
GENERIC_PARSER_LIVE_TEST=1 pytest -m live -q
```
