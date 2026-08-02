# GenericParser

Wiederverwendbarer Python-Parser und mobile PWA für Kleinanzeigen-Suchen, entwickelt für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.42.3`
- **Paketversion:** `0.42.3`
- **Build-ID:** `gp-0423-20260802-1`
- **API-Vertrag:** `match-v6.1-page-worker`
- **Technischer Abschluss-Commit:** `9c8841fecac53ffaa127a7ed83ca94492a260a88`
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
- Abschluss der Pagination, sobald die gemeldete Gesamtzahl erreicht ist

## Architektur 0.42.3

```text
Browser/PWA
→ Controller und Deployment-Handshake
→ minimaler Cloudflare-ASGI-Bootstrap
→ app-freier Search-Service
→ genau eine Kleinanzeigen-Ergebnisseite
→ Matching und Konsistenzprüfung
→ Abschlussprüfung gegen reported_total und Seitengröße
→ strukturierte JSON-Antwort
```

UI, Controller, Worker, Eventlog und PWA-Cache verwenden dieselbe Version, Build-ID und denselben API-Vertrag. Eine Live-Suche wird nur freigegeben, wenn der Handshake vollständig konsistent ist.

0.42.3 verhindert unnötige Folgeseiten: Sobald die bisher abgedeckte Ergebnismenge die von Kleinanzeigen gemeldete Gesamtzahl erreicht, wird die Suche mit `reported_total_reached` beendet. Eine kurze HTML-Seite beendet die Suche mit `short_html_page`.

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
