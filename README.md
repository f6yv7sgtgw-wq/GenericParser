# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.44.6.5`
- **Paketversion:** `0.44.6.5`
- **Build-ID:** `gp-04465-20260804-1`
- **API-Vertrag:** `match-v6.11.6-clean-rollback-04462`
- **Operative Referenzbasis:** `0.44.6.2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Rollback-Referenzcommit:** `f55f31bcd878ec1edb0b8fc0ee9b5330c8ef0a0a`
- **Zielplattform:** Cloudflare Workers Free

## Sauberer Rollback 0.44.6.5

0.44.6.5 nimmt die experimentellen Änderungen aus 0.44.6.3 und 0.44.6.4 aus dem aktiven Pfad. Die Version verwendet wieder das bestätigte Verhalten von 0.44.6.2 unter einer neuen, konsistenten Deployment-Identität.

```text
Worker-Einstieg und FastAPI-Bootstrap wie 0.44.6.2
→ unveränderter 0.44.4-Suchkern
→ höchstens sieben Ergebnisse pro Arbeitspaket
→ fünf Sekunden Browserpause
→ echte Weiter-Navigation
→ Suchstand nach jedem Paket speichern
```

Recovery entspricht ebenfalls 0.44.6.2:

```text
503/1101 und retry_exhausted
→ Suchstand speichern
→ 90 Sekunden Ruhezeit
→ /api/version prüfen
→ genau ein automatischer Resume-Versuch
→ danach manueller Fallback
```

Nicht aktiv sind:

- `/api/recovery-probe` aus 0.44.6.3/0.44.6.4
- zwei oder mehr automatische Resume-Zyklen
- Lazy-ASGI-Bootstrap aus 0.44.6.4
- direkter leichter Search-Worker aus 0.44.5.x

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

## Lokale Tests

```bash
python -m pytest -q tests/test_clean_rollback_v04465.py
node --check cloudflare/public/controller-04465.js
node --check cloudflare/public/auto-resume-04465.js
node --check cloudflare/public/eventlog-04465.js
```

## Abnahme von 0.44.6.5

1. `/api/version` meldet Version, Build und API-Vertrag konsistent.
2. Eine neue Suche verarbeitet das erste Arbeitspaket wie 0.44.6.2.
3. Ergebnisse, Pagination, Preise, Bilder und Ampel entsprechen 0.44.6.2.
4. Der aktive Worker enthält keinen 0.44.6.4-Lazy-Bootstrap.
5. Der Browser verwendet die einmalige 0.44.6.2-Recovery über `/api/version`.
6. Nach einem Terminalfehler bleibt der Suchstand erhalten.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
