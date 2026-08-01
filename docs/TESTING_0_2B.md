# Testen des Diagnose-Webinterfaces 0.2b

## Lokal starten

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
generic-parser-web
```

Danach im Browser `http://127.0.0.1:8000` öffnen.

Unter Windows kann `start-interface.bat`, unter macOS/Linux `./start-interface.sh` verwendet werden.

## Docker

```bash
docker compose up --build
```

Die Oberfläche ist anschließend unter `http://127.0.0.1:8000` erreichbar. Gespeicherte Live-Fixtures landen in `data/fixtures`.

## Empfohlene Abnahmereihenfolge

1. **Fixture „Ergebnisse + TOP-Duplikat“:** zwei Listings, ein Duplikat und ein Kartenfehler.
2. **Nulltreffer:** Seite wird als `no_results` erkannt und nicht als Layoutfehler.
3. **Layoutänderung:** Oberfläche zeigt einen klaren Parserfehler.
4. **Block-/CAPTCHA-Seite:** Oberfläche zeigt einen Blockierungsfehler.
5. **HTML-Modus:** eigenes gespeichertes HTML einfügen und parsen.
6. **Live-Modus:** zunächst bundesweit und mit einem einzelnen Suchbegriff testen.
7. **Lokale Suche:** PLZ und interne Location-ID gemeinsam setzen; anschließend Radiusprüfung verwenden.

## Schutzmaßnahmen

- Live-Suchen werden serverseitig serialisiert; parallele Abrufe werden abgewiesen.
- Zwischen mehreren URLs liegt ein Request-Delay.
- Blockierungen und Challenges werden nicht als Nulltreffer interpretiert.
- Live-Fixtures werden nur bei gesetzter Checkbox gespeichert.
- Das Interface kann ausschließlich von GenericParser erzeugte Kleinanzeigen-URLs abrufen.

## Bekannte Grenze von 0.2b

Die Oberfläche zeigt und diagnostiziert Ergebnislisten. Produkt-Matching, Preisbewertung, SQLite, Hintergrund-Worker und Benachrichtigungen beginnen in späteren Versionen.
