# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.44.6.3`
- **Paketversion:** `0.44.6.3`
- **Build-ID:** `gp-04463-20260804-1`
- **API-Vertrag:** `match-v6.11.4-reference-recovery-hardening`
- **Arbeitsreferenz:** `0.44.6.2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## Recovery-Hardening 0.44.6.3

0.44.6.3 verändert nicht Parser, Pagination, Extraktion oder Ampel. Die Version verbessert ausschließlich die automatische Fortsetzung nach temporären Cloudflare-Ausfällen.

```text
Terminalfehler: 1101, 1102 oder wiederholtes HTML-503
→ Suchstand speichern
→ 90 s Ruhezeit ±10 %
→ /api/recovery-probe
→ Python-Runtime, ASGI, Search-Service und Referenzkern prüfen
→ Auto-Resume 1
→ bei erneutem Terminalfehler 180 s ±10 %
→ erneut vollständigen Suchpfad prüfen
→ Auto-Resume 2
→ danach nur noch manuell fortsetzen
```

Die Recovery-Probe lädt den Search-Service und validiert das Request-Modell, die Suchfunktion und den Referenzkern `generic_parser.search_service_v0444`. Sie führt selbst keine Kleinanzeigen-Suche aus.

Zusätzliche Diagnosewerte:

- `cf-error-type`
- `cf-error-origin`
- `Retry-After`
- Ray-ID
- Recovery-Zyklus und Wartezeit
- Probe-Versuch und Probe-Dauer
- sichtbare Recovery-Kachel in der Suchoberfläche

## Unveränderter Referenzkern

- höchstens sieben Karten pro Worker-Aufruf
- fünf Sekunden Pause zwischen erfolgreichen Arbeitspaketen
- echte Kleinanzeigen-Weiter-Navigation
- robuste Titel-, Preis- und Kartenextraktion
- persistenter Suchstand und Fortsetzung
- Deduplizierung
- Pflicht- und Ausschlussbegriffe
- Maximalpreis und Richtwert
- Ampelbewertung nur für gesetzte Kriterien
- leere optionale Felder werden ignoriert
- Datenkonsistenzprüfung

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

## Lokale Tests

```bash
python -m pytest -q tests/test_recovery_hardening_v04463.py
node --check cloudflare/public/controller-04463.js
node --check cloudflare/public/auto-resume-04463.js
node --check cloudflare/public/eventlog-04463.js
```

## Abnahme von 0.44.6.3

1. `/api/version` meldet Version, Build und API-Vertrag konsistent.
2. `/api/recovery-probe` meldet `status: ready` und den geladenen 0.44.4-Referenzkern.
3. Normale Suchergebnisse entsprechen 0.44.6.2.
4. Nach einem Terminalfehler wird `recovery_scheduled` protokolliert.
5. Nach erfolgreicher Probe folgen `recovery_probe_ready`, `recovery_resume_start` und `recovery_resume_running`.
6. Die Suche setzt auf dem gespeicherten Arbeitspaket fort.
7. Es entstehen keine zusätzlichen Dubletten.
8. Nach höchstens zwei automatischen Fortsetzungen bleibt die manuelle Fortsetzung verfügbar.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
