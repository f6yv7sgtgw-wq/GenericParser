# GenericParser

Wiederverwendbarer Kleinanzeigen-Parser und mobile PWA für die Einbindung in **Evercade**, **SNES-PAL-Sammlung** und weitere Projekte.

## Aktueller Stand

- **Version:** `0.45.0`
- **Build-ID:** `gp-0450-20260805-1`
- **Modulvertrag:** `generic-parser-module-v1`
- **Stabile Rückfallreferenz:** `0.44.6.5`
- **Fachlicher Suchkern:** unverändert aus `0.44.4`
- **Zielplattform:** Cloudflare Workers Free

## Ziel von 0.45

0.45 verändert nicht, wie gesucht wird. Der bestätigte Suchfluss aus 0.44.6.5 bleibt erhalten. Neu ist eine stabile Integrationsgrenze für andere Projekte:

```text
Evercade / SNES / weiteres Projekt
→ ModuleSearchProfile
→ /api/module/v1/search
→ einheitliche Listings, Pagination, Summary und Ampel
```

## Modul-Endpunkte

- `GET /api/module/v1/capabilities`
- `POST /api/module/v1/profile/validate`
- `POST /api/module/v1/search`
- `GET /api/module/v1/self-test?enabled=true`
- `POST /api/search` bleibt als kompatibler UI- und Referenzpfad erhalten

## Beispielprofil

```json
{
  "profile": {
    "profile_id": "evercade:interplay-1",
    "display_name": "Evercade · Interplay Collection 1",
    "query": "Evercade Interplay Collection 1",
    "required_terms": [],
    "excluded_terms": [],
    "model_patterns": [],
    "brands": ["Evercade", "Blaze"],
    "max_price": 35,
    "market_value": 30,
    "accept_bundles": false,
    "accept_incomplete": false
  },
  "page": 0,
  "source": "auto",
  "debug": {
    "enabled": false
  }
}
```

Leere optionale Felder werden nicht an den Referenzkern weitergegeben und daher nicht ausgewertet.

## Einheitliches Ergebnisformat

Die Modulantwort enthält:

- `listings`: ID, Titel, URL, Bild, Preis, Ort, Match und Ampel
- `pagination`: aktuelle Seite, nächste Seite, Abschluss und Quelle
- `summary`: abgerufen, sichtbar, ausgeblendet, eindeutig und Ampelzählung
- `deployment`: Version, Build und Referenzstand
- `debug`: nur bei ausdrücklich aktiviertem Debugmodus

## Projektadapter

```python
from generic_parser import evercade_profile, snes_pal_profile

profile = evercade_profile(
    "Interplay Collection 1",
    market_value=30,
    max_price=35,
)

snes = snes_pal_profile(
    "Super Metroid",
    market_value=70,
)
```

Die Adapter übersetzen projektspezifische Titel, Varianten und Preise in den gemeinsamen Modulvertrag. Sammlungs- und Kaufentscheidungen bleiben in den aufrufenden Projekten.

## Deaktivierbare Debug-Logs

Debug-Logs sind standardmäßig aus.

Aktivierungsmöglichkeiten:

- Schalter **Debug-Logs aktivieren** in der mobilen Oberfläche
- Header `X-GenericParser-Debug: 1`
- Feld `debug.enabled: true` beim Modulrequest

Ohne Aktivierung werden keine zusätzlichen Debugereignisse und keine Payloaddaten erzeugt. Payloadlogging bleibt auch im Debugmodus standardmäßig aus.

## Deaktivierbare Modultests

Die Selbsttests sind ebenfalls standardmäßig aus und verwenden kein Kleinanzeigen-Netzwerk.

Aktivierung:

- Schalter **Netzwerkfreie Modultests aktivieren**
- Schaltfläche **Modultest ausführen**
- `GET /api/module/v1/self-test?enabled=true`
- Header `X-GenericParser-Tests: 1`

Geprüft werden Profilnormalisierung, Ignorieren leerer Felder, Ergebnisvertrag, Ampelzusammenfassung sowie Evercade- und SNES-Adapter.

## Unverändert gegenüber 0.44.6.5

- Controller- und UI-Suchfluss
- ASGI-Workerpfad
- 0.44.4-Suchkern
- höchstens sieben Karten pro Arbeitspaket
- fünf Sekunden normale Pause
- echte Kleinanzeigen-Weiter-Navigation
- Titel-, Preis- und Bildextraktion
- Deduplizierung und persistenter Suchstand
- Pflicht- und Ausschlussbegriffe
- Maximalpreis, Richtwert und Ampel
- bestehendes Retry- und Recovery-Verhalten

## Tests

```bash
python -m pytest -q tests/test_module_v0450.py
node --check cloudflare/public/module-debug-0450.js
node tests/check_module_debug_v0450.js
```

Der reguläre CI-Lauf liegt in `.github/workflows/module-0450.yml`. Die alte 0.44.6.6-Experiment-Suite ist nur noch manuell ausführbar.

## Live-Abnahme

1. `/api/version` meldet `0.45.0`, `gp-0450-20260805-1` und `generic-parser-module-v1`.
2. Die bestehende Suche liefert denselben Ablauf wie 0.44.6.5.
3. `/api/module/v1/capabilities` meldet Kleinanzeigen, Evercade und SNES-PAL.
4. Profilvalidierung ignoriert leere Regeln.
5. Der Selbsttest ist ohne Aktivierung gesperrt und mit Aktivierung netzwerkfrei ausführbar.
6. Debug-Logs erscheinen nur bei eingeschaltetem Schalter.

Weitere Informationen: [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md) und [`VERSION.json`](VERSION.json).
