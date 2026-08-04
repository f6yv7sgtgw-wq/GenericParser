# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Testversion:** `0.44.6.6`
- **Build-ID:** `gp-04466-20260804-2`
- **API-Vertrag:** `match-v6.11.7-rollback-04465-cooldown-test`
- **Stabile Referenz:** `0.44.6.5`
- **Laufzeitbasis:** `0.44.6.2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## 0.44.6.6 Build 2 – wiederholter Cooldown-Test

Gegenüber der stabilen Referenz 0.44.6.5 wird ausschließlich die normale Seitenpause an festen Ergebnisschwellen ersetzt:

```text
120 eindeutige Treffer erreicht
→ statt der normalen 5 Sekunden 90 Sekunden warten
→ automatisch weiter

240 eindeutige Treffer erreicht
→ erneut 90 Sekunden warten
→ automatisch weiter

360, 480, 600 …
→ gleicher Ablauf bei jedem weiteren Vielfachen von 120
```

Die Pause läuft im Browser. Währenddessen erhält der Worker keinen neuen Suchauftrag. Der Suchstand bleibt gespeichert. Die nächste Schwelle wird in `localStorage` gehalten, sodass dieselbe Schwelle nicht doppelt ausgelöst wird.

Eventlog-Einträge:

- `cooldown_threshold_reached`
- `cooldown_start`
- `cooldown_resume`
- `cooldown_cancelled`, falls während der Pause gestoppt wird

## Unverändert gegenüber 0.44.6.5

- ASGI-Workerpfad und FastAPI-Bootstrap
- unveränderter 0.44.4-Suchkern
- höchstens sieben Karten pro Arbeitspaket
- fünf Sekunden normale Pause außerhalb der Cooldown-Schwellen
- echte Kleinanzeigen-Weiter-Navigation
- Titel-, Preis-, Bild- und Kartenextraktion
- Deduplizierung und persistenter Suchstand
- Pflicht- und Ausschlussbegriffe
- Maximalpreis, Richtwert und Ampel
- einmalige 0.44.6.2-Fehler-Recovery nach 90 Sekunden
- Retry-Verhalten und Ergebnisdarstellung

0.44.6.6 bleibt ausdrücklich eine **Testversion**. 0.44.6.5 bleibt die stabile Referenz.

## Tests

```bash
python -m pytest -q tests/test_cooldown_v04466.py
node --check cloudflare/public/controller-04466.js
node tests/check_controller_runtime_v04466.js
```

## Live-Abnahme

1. `/api/version` meldet `0.44.6.6` und `gp-04466-20260804-2`.
2. Bis 120 Treffer entsprechen Ergebnisse und Ablauf 0.44.6.5.
3. Bei der ersten Schwelle erscheinen `cooldown_threshold_reached`, `cooldown_start` und nach 90 Sekunden `cooldown_resume` mit `threshold: 120`.
4. Bei der zweiten Schwelle erscheinen dieselben Ereignisse mit `threshold: 240`.
5. Außerhalb der Schwellen bleibt die normale 5-Sekunden-Pause aktiv.
6. Während jeder 90-Sekunden-Pause erfolgt kein `/api/search`-Request.
7. Es entstehen keine zusätzlichen Dubletten.
8. Fehler-Recovery und manuelles Stoppen bleiben funktionsfähig.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
