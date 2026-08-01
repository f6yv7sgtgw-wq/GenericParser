# Cloudflare Mobile Worker – 0.2c

Diese Variante stellt GenericParser als mobile PWA auf Cloudflare Workers bereit. Das Smartphone öffnet nur die Web-App; der Cloudflare Worker ruft genau eine Kleinanzeigen-Ergebnisliste ab und parst maximal 20 Treffer.

## Voraussetzungen

- Cloudflare-Konto
- Node.js und Wrangler 4.64 oder neuer
- `uv` 0.29.8 oder neuer
- `workers-py` 1.72 oder neuer

## Lokal testen

```bash
uv run --group cloudflare pywrangler dev
```

## Deployen

```bash
uv run --group cloudflare pywrangler login
uv run --group cloudflare pywrangler deploy
```

Nach dem Deployment zeigt Pywrangler die `workers.dev`-URL an. Diese URL kann auf iPhone oder Android zum Home-Bildschirm hinzugefügt werden.

## Zugriff schützen

Optional wird ein gemeinsames Token als Worker-Secret gesetzt:

```bash
uv run --group cloudflare pywrangler secret put APP_TOKEN
```

Das gleiche Token wird im mobilen Interface unter „Ort, Radius und Zugriff“ eingetragen und nur lokal im Browser gespeichert. Für einen produktiven Betrieb ist Cloudflare Access gegenüber einem gemeinsamen Token vorzuziehen.

## Worker-Grenzen

- eine Kleinanzeigen-Seite je Suche
- maximal 20 zurückgegebene Anzeigen
- keine Persistenz und kein Hintergrundlauf
- keine Detailseiten
- Blockierungen werden als HTTP 429 gemeldet

Die Begrenzungen sind absichtlich gewählt, um CPU-Zeit, Subrequests und das Risiko unnötiger Plattformzugriffe gering zu halten.
