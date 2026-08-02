# GenericParser 0.40.7

## Architektur-Fix

- Produktiver Worker importiert wieder direkt den stabilen Ein-Seiten-Worker aus 0.39.
- Keine Diagnose-Middleware, ContextVars oder verschachtelten 0.40.x-Wrapper im Worker-Laufzeitpfad.
- Genau ein zentraler Browser-Controller verwaltet Start, Stopp und Fortsetzen.
- Alte Event-Listener werden durch geklonte Schaltflächen zuverlässig entfernt.

## Sanfter Stopp

- Ein laufender Seitenrequest wird nicht mehr per AbortController abgebrochen.
- Die aktuelle Seite darf kontrolliert enden.
- Danach beendet sich die Suchschleife über `stopRequested`.
- Vor einer neuen Suche gilt eine echte zweisekündige Sperre.

## Eventlog

- Maximal 300 Einträge.
- Nahezu identische Ereignisse werden innerhalb von 1,5 Sekunden dedupliziert.
- Countdown-Status wird nicht mehr alle 200 ms protokolliert.
- Protokolliert werden Suchstart, Request-Start/-Ende, Stopp, Cooldown, Fehler und Cloudflare-Ray-ID.

## Kompatibilität

- Pagination-Fingerprints, gespeicherter Fortschritt und Ergebnis-Deduplizierung bleiben erhalten.
- 1101-HTML-Antworten werden clientseitig erkannt und ohne Retry als strukturierter Fehler dargestellt.
