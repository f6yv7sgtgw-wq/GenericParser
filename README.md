# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Testversion:** `0.44.6.6.1`
- **Build-ID:** `gp-044661-20260805-1`
- **API-Vertrag:** `match-v6.11.8-rollback-04465-cooldown120-recovery-control`
- **Stabile Referenz:** `0.44.6.5`
- **Laufzeitbasis:** `0.44.6.2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## 0.44.6.6.1 – 120-Sekunden-Test

Die Version übernimmt den funktionierenden Suchfluss aus 0.44.6.5 und verändert nur die browserseitigen Ruhe- und Fortsetzungsmechanismen.

```text
120 eindeutige Treffer erreicht
→ statt der normalen 5 Sekunden 120 Sekunden warten
→ automatisch weiter

240 eindeutige Treffer erreicht
→ erneut 120 Sekunden warten
→ automatisch weiter

360, 480, 600 …
→ gleicher Ablauf bei jedem weiteren Vielfachen von 120
```

Während der Pause erhält der Worker keinen neuen Suchauftrag. Der Suchstand bleibt gespeichert. Die Cooldown-Schicht bleibt fail-open: Kann sie nicht initialisiert werden, bleibt die Referenzsuche nutzbar.

## Recovery-Test

Nach einer terminalen 503-/1101-Kette:

```text
Suchstand speichern
→ 120 Sekunden warten
→ /api/version prüfen
→ Fortsetzen-Schaltfläche sichtbar und aktiv setzen
→ Fortsetzung auslösen
→ nach 10 Sekunden auf search_resume prüfen
→ bei Bedarf genau einmal erneut auslösen
```

Startet auch der zweite Steuerungsversuch keine neue Suchsession, bleibt der Suchstand erhalten und die UI fordert zum manuellen Fortsetzen auf.

Neue bzw. relevante Eventlog-Einträge:

- `cooldown_threshold_reached`
- `cooldown_start`
- `cooldown_resume`
- `auto_resume_scheduled`
- `auto_resume_health_ready`
- `auto_resume_start`
- `auto_resume_control_retry`
- `auto_resume_running`
- `auto_resume_manual_required`

## Unverändert gegenüber 0.44.6.5

- Controllerquelle und Suchereignisse
- ASGI-Workerpfad und FastAPI-Suchbootstrap
- unveränderter 0.44.4-Suchkern
- höchstens sieben Karten pro Arbeitspaket
- fünf Sekunden normale Pause außerhalb der Cooldown-Schwellen
- echte Kleinanzeigen-Weiter-Navigation
- Titel-, Preis-, Bild- und Kartenextraktion
- Deduplizierung und persistenter Suchstand
- Pflicht- und Ausschlussbegriffe
- Maximalpreis, Richtwert und Ampel
- Retry-Verhalten und Ergebnisdarstellung

0.44.6.6.1 bleibt eine **Testversion**. 0.44.6.5 bleibt die stabile Referenz.

## Tests

```bash
python -m pytest -q tests/test_cooldown_v04466.py
node --check cloudflare/public/controller-04466.js
node --check cloudflare/public/cooldown-04466.js
node --check cloudflare/public/auto-resume-04466.js
node tests/check_controller_runtime_v04466.js
node tests/check_cooldown_runtime_v04466.js
```

## Live-Abnahme

1. `/api/version` meldet `0.44.6.6.1` und `gp-044661-20260805-1`.
2. Die Oberfläche zeigt `Bereit` und aktiviert `Live-Suche starten`.
3. Eine neue Suche liefert vor 120 Treffern denselben Ablauf wie 0.44.6.5.
4. Bei 120 erscheinen `cooldown_threshold_reached`, `cooldown_start` und nach 120 Sekunden `cooldown_resume`.
5. Nach einem terminalen Fehler erscheinen `auto_resume_scheduled`, `auto_resume_health_ready` und `auto_resume_start`.
6. Die Recovery muss danach `search_resume` beziehungsweise `auto_resume_running` erzeugen.
7. Fehlt `search_resume` nach zehn Sekunden, erscheint `auto_resume_control_retry` und die Steuerung wird einmal erneut ausgelöst.
8. Es entstehen keine zusätzlichen Dubletten.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
