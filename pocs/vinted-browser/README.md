# Vinted Browser Run PoC

Isolierter Proof of Concept für die öffentliche Vinted-Suche mit echtem Chromium über Cloudflare Browser Run.

## Ziel

Der PoC beantwortet genau eine Frage: Kann eine Browser-Run-Session aus derselben Cloudflare-Umgebung die öffentliche Vinted-Katalogseite laden und sichtbare Item-Links extrahieren, obwohl der bisherige `httpx`-Adapter bereits beim Startseiten-Bootstrap HTTP 403 erhält?

Der PoC ist bewusst **nicht** in den GenericParser-Suchkern integriert.

## Verhalten

- `GET /health` liefert PoC-Identität und Modus.
- `GET /search?q=Evercade` öffnet `https://www.vinted.de/catalog?search_text=Evercade&order=newest_first` in Chromium.
- Es werden ausschließlich öffentlich gerenderte Links mit `/items/<id>` ausgewertet.
- Ausgabe: `id`, `title`, `price`, `url`, `source` plus Browserdiagnose.
- Bei HTTP 401/403/429 oder sichtbarer Human-Verification/CAPTCHA-Seite liefert der PoC `status: blocked`.
- Kein Login, keine Benutzer-Cookies, keine Proxy-Rotation, kein CAPTCHA-/Challenge-Solving und kein Aufruf privater Accountfunktionen.

## Cloudflare

Der Worker nutzt ein Browser-Run-Binding namens `BROWSER` und `@cloudflare/puppeteer`.

```json
"browser": { "binding": "BROWSER" }
```

Produktionsname: `genericparser-vinted-poc`.

## Erfolgsbedingung

Der PoC ist erfolgreich, wenn ein Live-Aufruf mit `q=Evercade`:

1. keine Access-Challenge erkennt,
2. mindestens einen öffentlichen `/items/`-Link findet,
3. mindestens einen normalisierten Vinted-Treffer zurückliefert.

Erst danach wird über eine Integration in GenericParser entschieden.
