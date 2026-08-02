# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.42.7`
- **Paketversion:** `0.42.7`
- **Build-ID:** `gp-0427-20260803-1`
- **API-Vertrag:** `match-v6.1-page-worker`
- **Zielplattform:** Cloudflare Workers Free
- **Worker-Modell:** CPU-schonende virtuelle Arbeitspakete

## Ursache der bisherigen Abbrüche

Die Cloudflare-Traces weisen den Fehler eindeutig als `Worker exceeded CPU time limit` aus. Der frühere Python-Pfad baute für jede Kleinanzeigen-Seite einen vollständigen BeautifulSoup-DOM auf, normalisierte und bewertete alle Karten und überschritt dadurch das CPU-Budget des Free-Tarifs.

## Architektur 0.42.7

```text
Browser/PWA
→ konsistenter Versions-Handshake
→ 5 Sekunden Pause zwischen Aufrufen
→ minimaler Cloudflare-ASGI-Bootstrap
→ CPU-schonender Search-Service
→ eine Kleinanzeigen-Quellseite wird in vier virtuelle Arbeitspakete zerlegt
→ höchstens sieben Karten pro Worker-Aufruf
→ einfache, begrenzte HTML-Extraktion ohne vollständigen DOM
→ Suchstand nach jedem Paket speichern
→ nächstes Paket als eigener Worker-Aufruf
```

Die Ausführung ist bewusst langsam. Eine Quellseite mit ungefähr 25 Anzeigen benötigt bis zu vier einzelne Worker-Aufrufe. Der Browser wartet zwischen den Aufrufen fünf Sekunden und kann den gespeicherten Stand später fortsetzen.

## Kernfunktionen

- Kleinanzeigen-Suche in kleinen CPU-schonenden Arbeitspaketen
- höchstens sieben Karten pro Worker-Invocation
- keine vollständige BeautifulSoup-DOM-Rekonstruktion im Free-Tarif-Pfad
- persistenter Suchstand und Fortsetzung
- Deduplizierung über alle Arbeitspakete
- Pflicht- und Ausschlussbegriffe sowie Maximalpreis im leichten Matching
- sanfter Suchstopp und Session-Isolation
- Eventlog mit Request-, Paket-, Versions- und Fehlerdaten
- Deployment-Handshake zwischen UI, Controller und Worker
- PWA für Mobilgeräte
- Abschluss, sobald die gemeldete Gesamtzahl oder eine kurze Quellseite erreicht ist

## Versionskonsistenz

UI, Controller, Worker, Eventlog und PWA-Cache verwenden gemeinsam:

```text
Version:     0.42.7
Build-ID:    gp-0427-20260803-1
API-Vertrag: match-v6.1-page-worker
```

Eine Live-Suche wird nur freigegeben, wenn der Handshake vollständig konsistent ist.

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
