# GenericParser 0.40.3

## Behoben

- Eine manuell gestoppte Suche wird nicht mehr als `retry_exhausted` oder `undefined` angezeigt.
- Alte Requests, Retry-Countdowns und Suchschleifen werden vor dem Start einer neuen Suche vollständig beendet.
- Die neue Suche wartet auf das Ende der vorherigen Session und startet erst danach.
- Laufende `/api/search`-Requests werden über einen eigenen `AbortController` abgebrochen.
- Alte Ergebnisse, Diagnosewerte und URLs werden vor einer neuen Suche zurückgesetzt.
- Der gespeicherte Suchstand bleibt nach einem manuellen Stopp fortsetzbar.

## Session-Ablauf

1. Aktive Suche erhält das Stoppsignal.
2. Laufender Request wird abgebrochen.
3. Retry oder Countdown wird beendet.
4. Die alte Suchschleife wird vollständig abgewartet.
5. Ergebnisansicht und Diagnose werden zurückgesetzt.
6. Erst dann beginnt die neue Suche mit eigener Session-ID.

## Beibehaltet

- Seitenfingerabdrücke und Schutz vor wiederholten Ergebnisseiten aus 0.40.1.
- Gespeicherter Suchfortschritt und Wiederaufnahme.
- Adaptive Pausen, Backoff, Deduplizierung und Datenkonsistenzprüfung.
