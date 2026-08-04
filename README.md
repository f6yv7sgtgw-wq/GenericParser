# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Testversion:** `0.44.6.6`
- **Build-ID:** `gp-04466-20260804-3`
- **API-Vertrag:** `match-v6.11.7-rollback-04465-cooldown-test`
- **Stabile Referenz:** `0.44.6.5`
- **Laufzeitbasis:** `0.44.6.2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## 0.44.6.6 Build 3 – referenzsicherer Cooldown-Test

Build 2 blockierte den Start, weil der Wrapper die Funktion `countdown()` fälschlich in `controller-0411.js` suchte. Sie liegt jedoch in `app.js`.

Build 3 stellt daher zuerst den funktionierenden Controllerfluss aus 0.44.6.5 wieder her. Die Testpause ist jetzt ein separates, nach `app.js` geladenes Skript:

```text
app.js aus der Referenz
→ cooldown-04466.js umschließt nur countdown()
→ controller-04466.js startet denselben Controller wie 0.44.6.5
```

Die Cooldown-Schicht ist **fail-open**: Kann sie nicht geladen oder initialisiert werden, bleibt die Suche aus 0.44.6.5 funktionsfähig.

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

Während der Pause erhält der Worker keinen neuen Suchauftrag. Der Suchstand bleibt gespeichert. Eine unterbrochene Pause wird nach einem Reload nur für ihre verbleibende Dauer fortgesetzt.

Eventlog-Einträge:

- `cooldown_threshold_reached`
- `cooldown_start`
- `cooldown_resume`
- `cooldown_cancelled`

## Unverändert gegenüber 0.44.6.5

- Controllerquelle und Start-/Stop-/Fortsetzen-Ereignisse
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

0.44.6.6 bleibt eine **Testversion**. 0.44.6.5 bleibt die stabile Referenz.

## Tests

```bash
python -m pytest -q tests/test_cooldown_v04466.py
node --check cloudflare/public/controller-04466.js
node --check cloudflare/public/cooldown-04466.js
node tests/check_controller_runtime_v04466.js
node tests/check_cooldown_runtime_v04466.js
```

## Live-Abnahme

1. `/api/version` meldet `0.44.6.6` und `gp-04466-20260804-3`.
2. Die Oberfläche zeigt `Bereit` und aktiviert `Live-Suche starten`.
3. Eine neue Suche liefert vor 120 Treffern denselben Ablauf wie 0.44.6.5.
4. Bei 120 erscheinen `cooldown_threshold_reached`, `cooldown_start` und nach 90 Sekunden `cooldown_resume`.
5. Bei 240 erscheint dieselbe Ereignisfolge erneut.
6. Außerhalb der Schwellen bleibt die normale 5-Sekunden-Pause aktiv.
7. Während jeder 90-Sekunden-Pause erfolgt kein `/api/search`-Request.
8. Es entstehen keine zusätzlichen Dubletten.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
