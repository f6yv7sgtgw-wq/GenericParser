# Cloudflare Mobile Worker – 0.45.0

Diese Variante stellt GenericParser als mobile PWA und als versioniertes Modul `generic-parser-module-v1` auf Cloudflare Python Workers bereit.

## Laufzeit

```text
PWA oder Projekt
→ FastAPI/ASGI im Python Worker
→ ein Kleinanzeigen-Arbeitspaket
→ höchstens sieben normalisierte Karten
```

Die PWA koordiniert weitere Pakete mit mindestens fünf Sekunden Pause, speichert den Fortschritt lokal und dedupliziert Anzeigen-IDs. Der Worker selbst enthält keine dauerhafte Suchdatenbank und keinen Hintergrundscheduler.

## Lokal testen

```bash
uv sync --group cloudflare --extra dev
uv run --group cloudflare pywrangler dev
```

## Deployen

```bash
uv run --group cloudflare pywrangler login
uv run --group cloudflare pywrangler deploy
```

Der verbindliche GitHub-, Deployment- und Live-Prüfprozess steht in [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).

## Zugriff schützen

Optionales Worker-Secret:

```bash
uv run --group cloudflare pywrangler secret put APP_TOKEN
```

Suchclients senden es als `X-GenericParser-Token`. Für breitere Nutzung ist Cloudflare Access gegenüber einem gemeinsam verteilten Token vorzuziehen.

## Aktive Grenzen

- eine Kleinanzeigen-Quellseite wird pro Request geladen,
- höchstens sieben Karten werden pro virtuellem Arbeitspaket verarbeitet,
- bis zu vier Pakete bilden eine typische Quellseite ab,
- keine Detailseiten,
- keine Worker-Persistenz, Queue oder Benachrichtigung,
- Debug und Selbsttests standardmäßig aus,
- Selbsttests ohne Kleinanzeigen-Abruf,
- echte Langläufe bleiben durch den Free-Tarif begrenzt.

Die vollständigen Plattformzahlen, Funktionsgrenzen und Projektbeispiele stehen in [`../docs/API_0.45.0.md`](../docs/API_0.45.0.md).
