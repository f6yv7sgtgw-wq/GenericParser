# GenericParser 0.39.2

## Wählbarer Suchumfang

- Schneller Ausschnitt: 5 Seiten
- Erweiterter Ausschnitt: 20 Seiten (Standard)
- Bis zum Ende suchen: maximal 500 Seiten bzw. bis zum echten Suchende

## Kontrollierte Seitenfortsetzung

Jede Worker-Anfrage verarbeitet weiterhin genau eine Kleinanzeigen-Ergebnisseite. Der Browser wartet zwischen den Seiten standardmäßig 0,4 Sekunden. Die Pause ist auf 0,25, 0,4, 0,8 oder 1,5 Sekunden einstellbar.

## Status und Bedienung

- `Worker arbeitet` während einer Seitenanfrage
- `Worker fertig` nach jeder abgeschlossenen Seite
- sichtbarer Countdown bis zur nächsten Seite
- laufende Anzeige der bereits geladenen eindeutigen Ergebnisse
- neue Schaltfläche `Suche stoppen`
- beim Stoppen bleibt die bereits geladene Ergebnisliste erhalten

## Stabilität

- eine fehlgeschlagene Seite wird nach kurzer Pause einmal wiederholt
- Deduplizierung bleibt über alle Seiten aktiv
- das Leerseiten-Fallback aus 0.39.1 bleibt erhalten
- Worker, PWA und Cache verwenden gemeinsam Version 0.39.2
