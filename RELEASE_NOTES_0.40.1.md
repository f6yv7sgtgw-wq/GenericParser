# GenericParser 0.40.1

## Pagination-Fix

- Jede Ergebnisseite erhält im Browser einen Fingerabdruck aus ihren Anzeigen-IDs.
- Erste und letzte Anzeigen-ID sowie der gekürzte Fingerabdruck werden in der Diagnose angezeigt.
- Wiederholt eine Folgeseite exakt ein bereits verarbeitetes ID-Set, stoppt die Suche sofort mit `pagination_repeated_page`.
- Die wiederholte Seite wird nicht erneut in Treffer-, Duplikat- oder Konsistenzsummen aufgenommen.
- Dadurch werden Endlosschleifen, unnötige Retries und anschließende HTTP-500-Fehler vermieden.
- Die konkret erwartete HTML-Seiten-URL wird inklusive `pageNum` angezeigt.
- Gespeicherte Suchstände enthalten die bereits gesehenen Seitenfingerabdrücke und bleiben fortsetzbar.

## Datenkonsistenz

Die bestehende Prüfung bleibt aktiv:

`abgerufen = eindeutig + Duplikate + ausgeblendet`

Bei einer wiederholten Seite wird der Stand vor der Wiederholung als konsistentes Ergebnis beendet.
