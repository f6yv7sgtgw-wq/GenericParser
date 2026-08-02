# GenericParser

Wiederverwendbarer Python-Parser und mobile PWA für Kleinanzeigen-Suchen, entwickelt für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.42.2`
- **Paketversion:** `0.42.2`
- **Build-ID:** `gp-0422-20260802-1`
- **API-Vertrag:** `match-v6.1-page-worker`
- **Produktions-Commit:** `05c77b77d31a34c88dd2721f975492a6bac899fb`
- **Worker-Modell:** app-freier Ein-Seiten-Suchservice mit minimalem Bootstrap

## Kernfunktionen

- Suche über Kleinanzeigen mit Mobile-API und HTML-Fallback
- seitenweise Verarbeitung ohne feste Ergebnisbegrenzung
- Matching, Scoring und Filterung
- Deduplizierung und konsistente kumulative Ergebnisliste
- Suchstand speichern und fortsetzen
- sanfter Suchstopp und Session-Isolation
- Eventlog mit Request-, Seiten-, Versions- und Fehlerdaten
- Deployment-Handshake zwischen UI, Controller und Worker
- PWA für Mobilgeräte

## Architektur 0.42.2

```text
Browser/PWA
→ Controller und Deployment-Handshake
→ minimaler Cloudflare-ASGI-Bootstrap
→ app-freier Search-Service
→ genau eine Kleinanzeigen-Ergebnisseite
→ Matching und Konsistenzprüfung
→ strukturierte JSON-Antwort
```

UI, Controller, Worker, Eventlog und PWA-Cache verwenden dieselbe Version, Build-ID und denselben API-Vertrag. Eine Live-Suche wird nur freigegeben, wenn der Handshake vollständig konsistent ist.

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

## Lokales Webinterface

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
generic-parser-web
```

Danach `http://127.0.0.1:8000` öffnen.

## Tests

```bash
python -m pytest -q
```

Der echte Kleinanzeigen-Live-Smoke-Test ist standardmäßig deaktiviert:

```bash
GENERIC_PARSER_LIVE_TEST=1 pytest -m live -q
```

## Versionshistorie

Die zusammengefasste Historie steht in [`CHANGELOG.md`](CHANGELOG.md). Die Zuordnung von Versionen, Build-IDs und Abschluss-Commits steht in [`docs/RELEASE_INDEX.md`](docs/RELEASE_INDEX.md).
