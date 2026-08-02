# GenericParser 0.40.2

## Session-Isolation

- Jede Suche erhält eine eindeutige Session-ID.
- Vor dem Start einer neuen Suche wird die vorherige Suchschleife kontrolliert gestoppt.
- Laufende `/api/search`-Requests werden per `AbortController` beendet.
- Retry-Countdowns und Seitenpausen der alten Suche werden vollständig abgewartet, bevor die neue Session startet.
- Alte SNES-Callbacks können dadurch nicht mehr den Status einer anschließend gestarteten Evercade-Suche überschreiben.
- Der Worker-Status zeigt beim Start kurz die neue Session und den Suchbegriff.

## Beibehalten

- Pagination-Fingerabdrücke und Wiederholungsschutz aus 0.40.1.
- Gespeicherter Suchfortschritt und Wiederaufnahme aus 0.40.
- Datenkonsistenzprüfung und adaptive Seitenpause.
