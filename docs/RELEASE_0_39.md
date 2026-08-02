# GenericParser 0.39

## Ziel

0.39 ersetzt die mehrseitige Worker-Schleife durch einen Page-Worker. Jede API-Anfrage verarbeitet exakt eine Kleinanzeigen-Ergebnisseite. Die Fortsetzung und Deduplizierung erfolgen im Browser.

## Änderungen

- eine Worker-Anfrage entspricht genau einer Ergebnisseite
- Browser fordert Folgeseiten automatisch nacheinander an
- sichtbarer Status: `Worker arbeitet`, `Worker fertig`, `Worker abgebrochen`
- Status enthält die aktuell verarbeitete Seite und die Zahl neuer Ergebnisse
- bereits geladene Ergebnisse bleiben bei einem späteren Fehler sichtbar
- breite ungefilterte Suchen mit mehr als 500 gemeldeten Treffern enden nach einem gekennzeichneten Ausschnitt
- HTML-Fallback erkennt Angaben wie `63 Ergebnisse` und `Mehr als 10.000 Ergebnisse`
- fehlerhafte Parserobjekte mit eingebettetem HTML werden verworfen
- Diagnose weist verworfene Datensätze separat aus
- API-Vertrag `match-v6-page-worker`

## Datenfluss

Browser → `/api/search` mit `page` und `source` → Worker verarbeitet eine Seite → JSON-Antwort → Browser dedupliziert → nächste Seite.

## Sicherheitsgrenzen

- maximal eine externe Ergebnisseite pro Worker-Anfrage
- maximal 125 Seiten pro Browsersuche
- bei unbekannter Gesamtzahl und ungefiltertem HTML-Fallback maximal 12 Seiten als transparenter Ausschnitt
