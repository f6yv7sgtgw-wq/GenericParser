# GenericParser 0.40.4

Stabilitäts-Hotfix für Cloudflare Error 1101.

## Änderungen

- Produktions-Worker importiert den bewährten Ein-Seiten-Worker `cloudflare_v039` direkt.
- Verschachtelte Wrapper-Kette aus 0.40, 0.40.1 und 0.40.3 wird im produktiven Pfad vermieden.
- Integrierte Session-Steuerung aus 0.40.3 bleibt erhalten.
- Cloudflare-HTML-Seiten mit `Error 1101` / `Worker threw exception` werden im Browser erkannt.
- 1101 wird als nicht wiederholbarer Fehler mit optionaler Ray-ID angezeigt.
- Keine 15/30/60-Sekunden-Retry-Schleife bei einer Worker-Ausnahme.
- Oberfläche, Worker und PWA-Cache verwenden 0.40.4.

## Erwartetes Verhalten

Bei einer normalen Suche verarbeitet der Worker weiterhin genau eine Kleinanzeigen-Seite je Anfrage. Falls Cloudflare dennoch eine 1101-Seite liefert, stoppt die aktuelle Suche sofort mit einer verständlichen Fehlermeldung und führt keine automatischen Retries aus.
