# GenericParser 0.34

## Schwerpunkt
Deployment- und Backend-Korrektur: Cloudflare lädt nun die aktuelle Matching-/Pagination-API statt des alten 0.2.0rc3-Endpunkts.

## Änderungen
- Produktiver Worker-Einstiegspunkt importiert `generic_parser.cloudflare_v03`.
- Worker- und Health-Version werden auf `0.34.0` gesetzt.
- Pagination, Matching, Scoring und Diagnosedaten werden nun tatsächlich serverseitig ausgeführt.
- Frontend und Service-Worker-Cache wurden auf 0.34 aktualisiert.
- Die Diagnose zeigt Seitenanzahl, eindeutige Treffer und Abbruchgrund aus dem aktiven Backend.

## Funktionstest
`/health` muss `0.34.0` melden. Im Diagnosefeld darf nicht mehr `0.2.0rc3` erscheinen.
