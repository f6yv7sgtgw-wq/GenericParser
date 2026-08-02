# GenericParser 0.35

## Schwerpunkt

Live-Suchen verwenden die paginierte Kleinanzeigen-Mobile-API als Primärquelle. Der HTML-Parser bleibt für den expliziten HTML-Modus und als Fallback erhalten.

## Änderungen

- Mobile-API-first für Live-Suchen
- Pagination bis leere, wiederholte oder vollständig duplizierte Seite
- HTML nur bei Mobile-Fehler oder leerer Mobile-Antwort
- API meldet `primary_source`, `source_used`, Seitenzahlen und Abbruchgrund
- Produktiver Cloudflare-Einstiegspunkt lädt die aktuelle 0.35-Anwendung
- Weboberfläche und Service-Worker-Cache auf 0.35 aktualisiert

## Validierung

- Wrangler-Einstiegspunkt: `src/generic_parser/cloudflare_worker.py`
- Aktive Anwendung: `src/generic_parser/cloudflare_v03.py`
- Health-Version: `0.35.0`
- 84 Tests bestanden
- 1 optionaler Live-Test planmäßig übersprungen
