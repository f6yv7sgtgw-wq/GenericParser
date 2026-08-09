# GenericParser 1.4 Cloudflare Worker

Der Paid Worker stellt die PWA und den Vertrag `generic-parser-module-v1` bereit. Eine Standardsuche kombiniert den bewährten Kleinanzeigen-Kern, das private Vinted Service Binding und eBay Deutschland über die offizielle Production Browse API.

## Voraussetzungen

- Cloudflare-Konto
- Node.js 22
- `uv`
- eBay Production App ID und Cert ID

## Lokale Secrets

`cloudflare/.dev.vars.example` nach `cloudflare/.dev.vars` kopieren und die beiden eBay-Werte nur lokal eintragen:

```dotenv
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
```

`.dev.vars` wird nicht eingecheckt. Für Produktion werden dieselben Namen als verschlüsselte Cloudflare Worker Secrets gesetzt. OAuth-Tokens bleiben nur bis zu ihrem Ablauf im Worker-Speicher; eBay-Treffer werden weder serverseitig noch in der Browser-IndexedDB persistiert.

## Lokal testen

```bash
uv run --group cloudflare pywrangler dev
```

## Deployen

```bash
uv run --group cloudflare pywrangler login
uv run --group cloudflare pywrangler deploy
```

Der GitHub-Produktionsworkflow verlangt zusätzlich `EBAY_CLIENT_ID` und `EBAY_CLIENT_SECRET` als GitHub Environment Secrets. Er überträgt beide Werte ausschließlich über stdin in den verschlüsselten Cloudflare-Secret-Speicher und prüft anschließend, dass die Bindings im Live-Worker sichtbar und nutzbar sind. Die Werte werden weder als normale Wrangler-Variablen gesetzt noch in Logs ausgegeben.

## Zugriff schützen

Optional wird ein gemeinsames Token als Worker-Secret gesetzt:

```bash
uv run --group cloudflare pywrangler secret put APP_TOKEN
```

Das gleiche Token wird im mobilen Interface unter „Ort, Radius und Zugriff“ eingetragen und nur lokal im Browser gespeichert. Für einen produktiven Betrieb ist Cloudflare Access gegenüber einem gemeinsamen Token vorzuziehen.

## Worker-Grenzen

- Kleinanzeigen bleibt auf dem bestätigten 0.44.4-Suchkern.
- Vinted nutzt das private `VINTED_BROWSER` Service Binding und höchstens drei Inline-Details; weitere Details laufen clientseitig in seriellen 3er-Batches.
- eBay nutzt `EBAY_DE`, 25 Browse-Treffer pro Seite und standardmäßig nur Festpreisangebote.
- Reine eBay-Auktionen werden nur mit `include_ebay_auctions: true` zurückgegeben.
- Bei unbekanntem Versand bleiben `shipping_cost`, `total_price` und der bewertete `price` leer.
- Fehler einer Quelle werden als degradierter Quellenstatus zurückgegeben; andere Quellen bleiben verfügbar.

Das Deployment-Gate prüft Release-Identität, alle drei Quellen, eBay-Markt und Transport, Festpreisstandard, Preissemantik sowie den vorhandenen Vinted-Detailpfad.
