# GenericParser 0.38

## Ziel

Dynamischer Suchumfang und vollständige Auswertung kleiner und mittlerer Kleinanzeigen-Suchen.

## Änderungen

- bis 100 gemeldete Treffer: vollständige automatische Auswertung
- 101 bis 500 Treffer: automatische Cursor-Fortsetzung über mehrere Worker-Anfragen
- mehr als 500 Treffer: transparenter Ausschnitt mit Filterempfehlung
- gezielte Suchen mit Pflichtbegriffen, Preis, Ort, Modell oder explizitem Limit werden unabhängig von der Gesamtzahl fortgesetzt
- korrigierte HTML-Seitennummerierung: interne Cursor-Seite 1 entspricht `pageNum=2`
- dadurch keine doppelte erste Seite mehr und deutlich weniger künstliche Duplikate
- getrennte Anzeige von gemeldeter Gesamtmenge, geladenen eindeutigen Ergebnissen, Seiten, Anfragen und Duplikaten
- Worker-, UI- und Service-Worker-Version auf 0.38 aktualisiert

## Erwartetes Verhalten

Eine ungefilterte Suche nach `evercade` mit etwa 63 gemeldeten Ergebnissen wird vollständig geladen. Eine sehr breite Suche wie `snes` mit mehreren Tausend Treffern bleibt ein klar gekennzeichneter Ausschnitt, bis der Suchraum durch Filter eingegrenzt wird.
