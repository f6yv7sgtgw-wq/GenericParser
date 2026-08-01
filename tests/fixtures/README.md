# HTML-Fixtures

Die Dateien bilden die für 0.2a relevanten Kleinanzeigen-Zustände reproduzierbar ab:

- `kleinanzeigen_results.html`: Ergebnisliste mit zwei Anzeigen, einem TOP-Duplikat und einer defekten Einzelkarte
- `kleinanzeigen_no_results.html`: reguläre Nulltrefferseite
- `kleinanzeigen_layout_changed.html`: erreichbare Seite ohne bekannte Kartenstruktur
- `kleinanzeigen_blocked.html`: CAPTCHA-/Challenge-Seite

Die Fixtures enthalten keine echten Kontaktdaten. Der optionale Live-Smoke-Test liegt in `tests/test_live_kleinanzeigen.py` und wird nur mit `GENERIC_PARSER_LIVE_TEST=1` aktiviert.
