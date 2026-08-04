# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade** und **SNES-PAL-Sammlung**.

## Aktueller Stand

- **Produktversion:** `0.44.6.4`
- **Paketversion:** `0.44.6.4`
- **Build-ID:** `gp-04464-20260804-1`
- **API-Vertrag:** `match-v6.11.5-lazy-bootstrap-recovery`
- **Arbeitsreferenz:** `0.44.6.2`
- **Recovery-Basis:** `0.44.6.3 Build 2`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## Befund aus 0.44.6.3 Build 2

Der Resume-Button war wieder funktionsfähig. Das Eventlog zeigte jedoch eine neue Endlossituation:

```text
Cloudflare 1101 auf dem gespeicherten Arbeitspaket
→ Recovery geplant
→ /api/recovery-probe
→ HTTP 500
→ Probe 2 und 3 ebenfalls HTTP 500
→ manueller Resume
→ erneut sofort Cloudflare 1101
```

Die Ursache war die Probe selbst: Sie importierte den vollständigen ASGI-, FastAPI- und Search-Service-Pfad und löste damit denselben schweren Import aus, den sie eigentlich absichern sollte.

## Recovery-Fix 0.44.6.4

0.44.6.4 trennt den leichten Worker-Einstieg vom eigentlichen Suchpfad:

```text
GET /api/version
GET /api/recovery-probe
→ direkte JSON-Antwort im WorkerEntrypoint
→ kein ASGI
→ kein FastAPI
→ kein Search-Service
→ kein generic_parser/__init__.py

POST /api/search
→ ASGI erst jetzt laden
→ FastAPI-Bootstrap erst jetzt laden
→ Search-Service erst jetzt laden
→ unveränderter 0.44.4-Suchkern
```

Die Recovery-Probe prüft nur noch:

- Worker-Einstieg erreichbar
- Version, Build und API-Vertrag konsistent
- lazy ASGI-Lader verfügbar
- Referenzkern 0.44.4 deklariert
- Paket-`__init__` wurde übersprungen

Damit ist die Probe bewusst leichter als der Vorgang, den sie freigibt. Scheitert anschließend der echte Suchimport, liefert der Worker nach Möglichkeit eine strukturierte HTTP-503-Antwort mit Phase und Fehlermeldung. Cloudflare-Limits können trotzdem weiterhin einen 1101/1102 erzeugen; dafür bleiben zwei gestaffelte Auto-Resumes erhalten.

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
python -m pytest -q tests/test_recovery_probe_v04464.py
node --check cloudflare/public/controller-04464.js
node --check cloudflare/public/auto-resume-04464.js
node --check cloudflare/public/eventlog-04464.js
```

## Abnahme von 0.44.6.4

1. `/api/version` antwortet mit HTTP 200 und `gp-04464-20260804-1`.
2. `/api/recovery-probe` antwortet mit HTTP 200 und `probe_mode: bootstrap_lazy`.
3. Die Probe meldet `probe_imports_search_service: false`.
4. Normale Suchergebnisse entsprechen 0.44.6.2.
5. Nach einem Terminalfehler folgen `recovery_probe_ready`, `recovery_resume_start` und `recovery_resume_running`.
6. Die Suche setzt auf dem gespeicherten Arbeitspaket fort.
7. Es entstehen keine zusätzlichen Dubletten.
8. Nach höchstens zwei automatischen Fortsetzungen bleibt die manuelle Fortsetzung verfügbar.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
