# GenericParser

Wiederverwendbarer Python-Parser für Kleinanzeigen, entwickelt für die spätere Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Status

**Version 0.2d / Paketversion `0.2.0rc2`.**

Zusätzlich zum lokalen Diagnoseinterface enthält das Projekt eine mobile PWA für Cloudflare Workers. 0.2d ergänzt den reproduzierbaren Produktionsprozess mit GitHub Actions, Cloudflare-Secrets, Smoke-Test und Rollback.

## In 0.2d enthalten

- alle Funktionen aus 0.2a bis 0.2c
- FastAPI-Einstiegspunkt für Python Workers
- asynchroner Cloud-Abruf über `httpx`
- CPU-reduzierter Kartenparser mit `SoupStrainer`
- maximal eine Ergebnisseite und 20 Anzeigen pro Worker-Anfrage
- mobile PWA mit Offline-App-Shell
- Demo- und direkter Browser-Dateimodus
- optionale Absicherung über `APP_TOKEN`
- Workers Static Assets und `wrangler.jsonc`
- automatisierte Worker-API- und PWA-Tests
- GitHub-Actions-Deployment mit Cloudflare-Secrets
- Produktions-Smoke-Test und Rollback-Skript
- dokumentierter Workers-Builds-Erststart

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

Die veröffentlichte `workers.dev`-URL kann auf dem Smartphone zum Home-Bildschirm hinzugefügt werden. Der vollständige Erststart, die GitHub-Secrets und der Rollback sind unter [`docs/DEPLOYMENT_0_2D.md`](docs/DEPLOYMENT_0_2D.md) beschrieben.

## Lokales Webinterface

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
generic-parser-web
```

Danach `http://127.0.0.1:8000` öffnen. Alternativ stehen Docker, `start-interface.sh` und `start-interface.bat` bereit.

## Tests

```bash
python -m pytest -q
```

Der echte Kleinanzeigen-Live-Smoke-Test ist standardmäßig deaktiviert:

```bash
GENERIC_PARSER_LIVE_TEST=1 pytest -m live -q
```
