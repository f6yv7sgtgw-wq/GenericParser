# Deployment und Live-Abnahme

Aktueller Prozess für GenericParser 0.45.0 und folgende Releases. Die frühere Anleitung `DEPLOYMENT_0_2D.md` bleibt als historische Referenz erhalten.

## Ziel

Der Python-Worker, die PWA und alle Modulendpunkte werden aus demselben geprüften Commit nach Cloudflare deployt. Ein Deployment gilt erst dann als bestätigt, wenn der veröffentlichte Build live dieselbe Version, Build-ID und denselben Vertrag meldet und ein begrenztes echtes Suchpaket bestanden hat.

## Voraussetzungen

GitHub Environment `production`:

- Secret `CLOUDFLARE_ACCOUNT_ID`,
- Secret `CLOUDFLARE_API_TOKEN`,
- optional Secret `APP_TOKEN`, wenn der Suchzugriff geschützt ist,
- optional Variable `CLOUDFLARE_WORKER_URL` als explizite Produktions-URL,
- optional Variable `CLOUDFLARE_LIVE_QUERY`; Standard ist `Evercade`.

Der API-Token benötigt nur die für das Deployment dieses Workers erforderlichen Cloudflare-Rechte. Secrets werden weder in `VERSION.json` noch in Release Notes abgelegt.

## GitHub Actions

`.github/workflows/cloudflare-deploy.yml` läuft bei runtime-relevanten Änderungen auf `main` sowie manuell über `workflow_dispatch`.

Der Workflow:

1. installiert die reproduzierbare Python-/Worker-Umgebung,
2. prüft Release-Metadaten, Modulvertrag, Browserassets und PWA,
3. validiert die beiden Cloudflare-Secrets,
4. deployt mit `pywrangler`,
5. verwendet die konfigurierte Produktions-URL oder ermittelt die ausgegebene `workers.dev`-URL,
6. prüft live Startseite, Manifest, Service-Worker, Health, Version, Header, Capabilities, Profilvalidierung, OpenAPI und den netzwerkfreien Selbsttest,
7. führt genau ein echtes Modul-Arbeitspaket mit höchstens sieben Karten aus.

Kann keine Deployment-URL bestimmt werden, schlägt der Workflow fehl. Der Live-Schritt wird nicht mehr stillschweigend übersprungen.

## Lokale Vorbereitung

```bash
python scripts/check_release_metadata.py
python -m pytest -q
node tests/check_module_debug_v0450.js
```

Lokale Worker-Entwicklung:

```bash
uv sync --group cloudflare --extra dev
uv run --group cloudflare pywrangler dev
```

## Manuelles Deployment

```bash
uv run --group cloudflare pywrangler login
uv run --group cloudflare pywrangler deploy
```

Optionaler Suchschutz:

```bash
uv run --group cloudflare pywrangler secret put APP_TOKEN
```

## Live-Prüfung

Nur Vertrag und netzwerkfreie Funktionen:

```bash
python scripts/check_deployment.py https://<worker>.<account>.workers.dev
```

Zusätzlich ein echtes, auf ein Arbeitspaket begrenztes Kleinanzeigen-Suchergebnis:

```bash
APP_TOKEN='<optional>' python scripts/check_deployment.py \
  https://<worker>.<account>.workers.dev \
  --live-search \
  --query Evercade
```

Der Test akzeptiert auch ein leeres natürliches Suchergebnis, sofern Vertrag, Paketgrenze und Dateninvarianten korrekt sind. HTTP-/Workerfehler werden nicht als Erfolg umgedeutet.

## Abnahmekriterien

- Version, Build-ID und Modulvertrag stimmen in Body und Response-Headern.
- PWA und Service-Worker enthalten den aktiven Release-Cache.
- Capabilities nennen Kleinanzeigen, Evercade und SNES-PAL.
- Leere optionale Regeln fehlen im übersetzten Legacy-Payload.
- Selbsttest ist standardmäßig gesperrt.
- Aktivierter Selbsttest ist erfolgreich und meldet `network_used: false`.
- OpenAPI enthält alle Modulpfade.
- Echtes Suchpaket enthält höchstens sieben Listings.
- `fetched = visible + hidden` und `visible = len(listings)`.
- Deployment-Identität in der Suchantwort entspricht dem aktiven Build.

## Free-Worker-Hinweis

Ein bestandener Ein-Paket-Test bestätigt Deployment, Vertrag und Grundfunktion. Er beweist keine zuverlässige lange Suche. Cloudflare Workers Free stellt aktuell nur 10 ms CPU pro HTTP-Aufruf bereit; die bekannten Abbrüche langer Browserketten und die begrenzte Recovery bleiben daher dokumentierte Restrisiken. Vollständige Zahlen und Auswirkungen stehen in `API_0.45.0.md`.

## Rollback

Stabile Referenz 0.44.6.5:

```text
ddba9bf55c999b349d98f1438b31a710bd570155
```

Cloudflare-Versionen anzeigen und gezielt zurückrollen:

```bash
./scripts/rollback-cloudflare.sh
./scripts/rollback-cloudflare.sh <CLOUDFLARE_VERSION_ID>
```

Nach einem Rollback wird derselbe Live-Check ohne `--live-search` und anschließend mit einem begrenzten Suchpaket gegen die erwartete Referenzidentität ausgeführt. Das aktuelle Skript liest die erwartete Identität aus dem ausgecheckten `VERSION.json`; für eine alte Version muss deshalb auch deren Commit ausgecheckt sein.
