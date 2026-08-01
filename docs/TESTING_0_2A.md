# 0.2a testen

## 1. Reproduzierbare Tests

```bash
python -m pip install -e ".[dev]"
pytest
```

Die normale Suite sendet keine Anfragen an Kleinanzeigen. Sie prüft URL-Aufbau,
Normalisierung, Kartenparsing, TOP-Deduplizierung, Kartenfehler, Nulltreffer,
Layoutwechsel, Blockseiten, Retry und Backoff gegen gespeicherte Fixtures und
Mock-HTTP-Antworten.

## 2. Gespeicherte Seite manuell prüfen

```bash
generic-parser parse-fixture tests/fixtures/kleinanzeigen_results.html
```

Als JSON:

```bash
generic-parser parse-fixture tests/fixtures/kleinanzeigen_results.html --json
```

## 3. Echte Suche ausführen

```bash
generic-parser fetch examples/snes_zelda_link_to_the_past.json --limit 20
```

Der Client ruft sequenziell ab, wartet zwischen Anfragen, setzt deutsche Browser-Header und behandelt 403/429 sowie 5xx mit kontrolliertem Backoff.

## 4. Location-ID ermitteln

Auf Kleinanzeigen einmal im Browser mit Ort und Radius suchen und die vollständige Such-URL kopieren. Die Zahl hinter `l` ist die interne Location-ID:

```bash
generic-parser location-id "https://www.kleinanzeigen.de/s-.../k0l1234r50"
```

Danach im Profil eintragen:

```yaml
postal_code: "37075"
location_id: 1234
radius_km: 50
```

Die PLZ darf niemals als `location_id` verwendet werden.

## 5. Radiuswirkung verifizieren

Für die Prüfung einen breiten Suchbegriff verwenden, der bundesweit deutlich mehr Ergebnisse liefert als im 5-km-Radius:

```bash
generic-parser verify-location profile.yaml --query videospiele --radius 5
```

Exit-Code `0` bedeutet unterschiedliche Kartenanzahlen. Exit-Code `3` bedeutet, dass die Wirkung nicht nachgewiesen wurde; dann Location-ID und Suchbegriff prüfen.

## 6. Optionaler Live-Smoke-Test

```bash
GENERIC_PARSER_LIVE_TEST=1 pytest -m live -q
```

Der Test erwartet keine feste Trefferzahl. Er bestätigt nur, dass die aktuelle Ergebnisliste ohne Block- oder Layoutfehler verarbeitet werden kann. Bei einer Blockierung nicht unmittelbar wiederholen.

## Bekannte Grenze von 0.2a

0.2a parst Ergebnislisten. Produkt-Matching, Gesuch-/Defektfilter und Scoring folgen in 0.3. Persistenz, wiederholte Läufe und Hintergrundbetrieb folgen in 0.4.
