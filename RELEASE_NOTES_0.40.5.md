# GenericParser 0.40.5

Diagnose-Build zur eindeutigen Lokalisierung verbleibender Cloudflare-1101-Ausnahmen.

## Neu

- Phasenmarkierung für Request-Eingang, Payload-Dekodierung, Mobile-URL, Mobile-Request, Mobile-Parsing, HTML-URL, HTML-Request und HTML-Parsing.
- Strukturierte Fehlerantwort mit Phase, Suchbegriff, Seite, Quelle, Ziel-URL, Laufzeit, Ray-ID, Fehlertyp und gekürztem Traceback.
- Antwortheader `X-GenericParser-Version`, `X-GenericParser-Phase` und `X-GenericParser-Elapsed-Ms`.
- Browserseitige Anreicherung strukturierter Fehler für eine direkt lesbare Diagnose.
- Cloudflare-1101 vor dem ASGI-Einstieg wird als Phase `runtime_before_asgi` ausgewiesen.
- Keine automatische Retry-Schleife für Diagnose- und 1101-Fehler.
- Diagnose-Endpunkt `/api/diagnostic-runtime`.

## Testziel

Eine Suche nach `Thule` starten und den vollständigen Fehlertext beziehungsweise Screenshot bereitstellen. Die ausgewiesene Phase grenzt den Absturz auf Runtime, URL-Aufbau, HTTP-Request oder Parsing ein.
