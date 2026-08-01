# Testanleitung 0.2c – Cloudflare Mobile Worker

## Automatisierte Tests

```bash
python -m pytest -q
```

Die Tests prüfen den FastAPI-Worker ohne Cloudflare-Konto, die asynchrone Ein-Seiten-Suche, HTML-Diagnose, Location-ID-Hilfe, Blockerkennung sowie alle PWA-Dateien.

## Cloudflare-Runtime lokal

```bash
uv run --group cloudflare pywrangler dev
```

Danach die angezeigte lokale URL aufrufen. Im Interface zuerst „Demo anzeigen“ und danach eine kontrollierte Live-Suche testen.

## Abnahme auf dem Handy

1. `workers.dev`-URL in Safari oder Chrome öffnen.
2. Demo anzeigen und Darstellung prüfen.
3. Eine breite Live-Suche ohne Ort starten.
4. Eine Kleinanzeigen-Such-URL mit Ort in die Location-ID-Hilfe einfügen.
5. PLZ, übernommene Location-ID und Radius verwenden.
6. Seite zum Home-Bildschirm hinzufügen und erneut öffnen.
7. Flugmodus aktivieren: Die App-Shell soll weiterhin öffnen, Live-Suchen müssen verständlich als nicht verfügbar erscheinen.

## Belastungsgrenze

0.2c ist ein manueller Diagnosebetrieb. Keine parallelen Suchläufe, keine automatische Wiederholung und keine Detailseiten. Erst reale Worker-Messwerte entscheiden, ob Cloudflare Free für das Parsing genügt.
