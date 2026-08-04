# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Testversion:** `0.44.6.6`
- **Build-ID:** `gp-04466-20260804-1`
- **API-Vertrag:** `match-v6.11.7-rollback-04465-cooldown-test`
- **Stabile Referenz:** `0.44.6.5`
- **Laufzeitbasis:** `0.44.6.2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## 0.44.6.6 – Ein-Änderungs-Test

Gegenüber der stabilen Referenz 0.44.6.5 wird ausschließlich eine geplante Pause ergänzt:

```text
mindestens 120 eindeutige Treffer verarbeitet
→ aktuelles Paket vollständig auswerten und speichern
→ vor dem nächsten /api/search-Aufruf 90 Sekunden warten
→ Suche automatisch mit demselben Zustand fortsetzen
```

Die Pause läuft im Browser. Währenddessen erhält der Worker keinen neuen Suchauftrag und ist vollständig idle. Der Worker selbst wird nicht für 90 Sekunden blockiert.

Die Testpause wird pro Suchsession höchstens einmal ausgeführt. Sie erzeugt folgende Eventlog-Einträge:

- `cooldown_threshold_reached`
- `cooldown_start`
- `cooldown_resume`
- `cooldown_cancelled`, falls während der Pause gestoppt wird

## Unverändert gegenüber 0.44.6.5

- ASGI-Workerpfad und FastAPI-Bootstrap
- unveränderter 0.44.4-Suchkern
- höchstens sieben Karten pro Arbeitspaket
- fünf Sekunden normale Pause
- echte Kleinanzeigen-Weiter-Navigation
- Titel-, Preis-, Bild- und Kartenextraktion
- Deduplizierung und persistenter Suchstand
- Pflicht- und Ausschlussbegriffe
- Maximalpreis, Richtwert und Ampel
- einmalige 0.44.6.2-Fehler-Recovery nach 90 Sekunden
- Retry-Verhalten und Ergebnisdarstellung

0.44.6.6 ist ausdrücklich **keine neue Referenz**. Bei einer Regression wird auf 0.44.6.5 zurückgeschaltet.

## Lokale Tests

```bash
python -m pytest -q tests/test_cooldown_v04466.py
node --check cloudflare/public/controller-04466.js
node --check cloudflare/public/auto-resume-04466.js
node --check cloudflare/public/eventlog-04466.js
node --check cloudflare/public/build-identity-04466.js
```

## Live-Abnahme

1. `/api/version` meldet `0.44.6.6` und `gp-04466-20260804-1`.
2. Bis zur Schwelle entsprechen Ergebnisse und Ablauf exakt 0.44.6.5.
3. Nach mindestens 120 eindeutigen Treffern erscheint die 90-Sekunden-Testpause.
4. Im Pausenfenster erfolgt kein weiterer `/api/search`-Request.
5. Nach 90 Sekunden startet das nächste Arbeitspaket automatisch.
6. Die Pause wird in derselben Session nicht erneut ausgelöst.
7. Es entstehen keine zusätzlichen Dubletten.
8. Fehler-Recovery und manuelles Stoppen bleiben funktionsfähig.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
