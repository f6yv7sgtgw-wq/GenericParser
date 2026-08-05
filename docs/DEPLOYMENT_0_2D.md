# GenericParser 0.2d – Cloudflare-Deployment

> Historische Anleitung für 0.2d. Der aktuelle Release- und Live-Abnahmeprozess steht in [`DEPLOYMENT.md`](DEPLOYMENT.md).

0.2d ergänzt den reproduzierbaren Produktionsprozess. Der fachliche Umfang bleibt unverändert: manuelle Testsuchen, keine automatischen Hintergrundläufe.

## Ziel

Nach der einmaligen Cloudflare-Autorisierung entsteht eine URL wie:

```text
https://generic-parser-mobile.<workers-subdomain>.workers.dev
```

## Erststart über Workers Builds

1. In Cloudflare **Workers & Pages** öffnen.
2. **Create application** → **Import a repository** wählen.
3. GitHub verbinden und `f6yv7sgtgw-wq/GenericParser` auswählen.
4. Branch `main` verwenden.
5. Workername exakt `generic-parser-mobile` setzen.
6. Deploy-Befehl `uv run --group cloudflare pywrangler deploy` verwenden.
7. Speichern und deployen.

## GitHub Actions

Der Workflow `.github/workflows/cloudflare-deploy.yml` testet Worker und PWA, deployt und prüft optional die Produktions-URL.

Erforderliche Secrets:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- optional `APP_TOKEN`

Optionale Variable:

- `CLOUDFLARE_WORKER_URL` mit der vollständigen HTTPS-URL

## Manuelles Deployment

```bash
uv run --group cloudflare pywrangler login
uv run --group cloudflare pywrangler deploy
```

Optionaler Zugriffsschutz:

```bash
uv run --group cloudflare pywrangler secret put APP_TOKEN
```

## Prüfung

```bash
python scripts/check_deployment.py https://generic-parser-mobile.<subdomain>.workers.dev
```

## Rollback

```bash
./scripts/rollback-cloudflare.sh
```

Oder gezielt:

```bash
./scripts/rollback-cloudflare.sh <VERSION_ID>
```

## Finale Abnahme

0.2d gilt als vollständig abgenommen, sobald eine echte HTTPS-URL vorliegt, `/health` Version `0.2.0rc2` meldet, die PWA auf dem Handy läuft und mindestens eine kontrollierte Live-Suche getestet wurde.
