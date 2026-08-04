# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.44.6.2`
- **Paketversion:** `0.44.6.2`
- **Build-ID:** `gp-04462-20260804-1`
- **API-Vertrag:** `match-v6.11.3-reference-auto-resume`
- **Zielplattform:** Cloudflare Workers Free
- **Funktionale Referenz:** `0.44.4`
- **Suchkern:** unveränderter Referenzpfad mit 7er-Arbeitspaketen

## Bestätigter Betriebsbefund

Der Referenzkern verarbeitet Treffer, Preise, Bilder, Ampelregeln und echte Weiter-Navigation korrekt. In langen Läufen kann der Cloudflare-Python-Worker jedoch nach einem HTML-503 beim anschließenden Retry mit `Cloudflare 1101 vor ASGI` abbrechen. Der Suchstand wird dabei zuverlässig gespeichert.

0.44.6.1 bot nach `retry_exhausted` ausschließlich die manuelle Schaltfläche **Letzte Suche fortsetzen**. 0.44.6.2 testet eine begrenzte automatische Recovery, ohne den Parser erneut umzubauen.

## Recovery-Ablauf 0.44.6.2

```text
Suchlauf mit gespeichertem Fortschritt
→ Terminalfehler: 1101 oder wiederholtes HTML-503
→ retry_exhausted
→ 90 Sekunden Ruhezeit
→ /api/version mit Cache-Bypass prüfen
→ Version, Build und API-Vertrag müssen übereinstimmen
→ vorhandene gespeicherte Suche einmal automatisch fortsetzen
→ bei erneutem Terminalfehler nur noch manuell fortsetzen
```

Grenzen:

- höchstens **ein** automatischer Resume-Versuch je Suchkette
- bis zu vier Bereitschaftsprüfungen im Abstand von 15 Sekunden
- kein unbegrenzter Retry-Kreis
- manueller Resume überschreibt eine wartende Automatik
- Löschen des Suchstands löscht auch den Recovery-Zustand
- Cloudflare garantiert nicht, dass die Bereitschaftsprüfung eine neue Worker-Instanz erzeugt

## Unveränderter Referenzkern

- höchstens sieben Karten pro Worker-Aufruf
- fünf Sekunden Pause zwischen erfolgreichen Arbeitspaketen
- echte Kleinanzeigen-Weiter-Navigation
- robuste Titel-, Preis- und Kartenextraktion
- persistenter Suchstand und Fortsetzung
- Deduplizierung über alle Arbeitspakete
- Pflicht- und Ausschlussbegriffe
- Maximalpreis und Richtwert
- Ampelbewertung nur für tatsächlich gesetzte Kriterien
- leere optionale Felder werden ignoriert
- Datenkonsistenzprüfung
- Eventlog mit Request-, Versions-, 503-, 1101- und Recovery-Ereignissen

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

## Abnahme von 0.44.6.2

Der Live-Test muss zeigen:

1. `auto_resume_scheduled` nach einer bestätigten 503/1101-Kette.
2. 90 Sekunden Ruhezeit und anschließende konsistente `/api/version`-Antwort.
3. `auto_resume_start` und eine neue `search_resume`-Session.
4. Fortsetzung auf dem gespeicherten Arbeitspaket statt Neustart bei Seite 1.
5. Keine erneut als neu gezählten Anzeigen.
6. Bei einem zweiten Terminalfehler kein weiterer automatischer Versuch.

Die Versionshistorie steht in [`CHANGELOG.md`](CHANGELOG.md). Die Roadmap steht in [`ROADMAP.md`](ROADMAP.md).
