# GenericParser 0.40.8

## Ziel

Seitengenaue Diagnose des verbleibenden Cloudflare-1101-Fehlers, ohne die Sucharchitektur aus 0.40.7 erneut zu verändern.

## Änderungen

- eindeutige Session-ID und Request-ID pro Seitenanfrage
- Protokollierung der tatsächlich gesendeten Such-Payload
- Seitennummer, sichtbare Seitennummer und angeforderte Quelle im Eventlog
- Marker `before_fetch`, `after_fetch`, `before_parse` und `after_parse`
- HTTP-Status, Content-Type und Content-Length-Header
- tatsächlich gelesene Antwortgröße in Bytes
- JSON-Erkennung und Parsergebnis
- Anzahl gelieferter Listings
- `next_page`, Pagination-Quelle, Stoppgrund und gemeldete Gesamtzahl
- Worker-Version und Worker-Phase aus Antwortheadern
- Ray-ID und Phase `runtime_before_asgi` bei Cloudflare Error 1101
- direkter stabiler Ein-Seiten-Worker aus 0.39 bleibt Grundlage
- Eventlog-Unterseite und PWA-Cache auf 0.40.8 aktualisiert

## Testziel

Nach einer erfolgreichen ersten Seite muss das Eventlog für die nächste Seite zeigen, ob der Ablauf bis `before_fetch`, `after_fetch`, `before_parse` oder `after_parse` gelangt. Dadurch lässt sich der Fehler eindeutig dem Netzwerkaufruf, der Cloudflare-Laufzeit oder der Antwortverarbeitung zuordnen.
