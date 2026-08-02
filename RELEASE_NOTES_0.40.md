# GenericParser 0.40

## Produktionsnahe Fortsetzungssuche

- Eine Worker-Anfrage verarbeitet weiterhin genau eine Kleinanzeigen-Seite.
- Temporäre interne Fehler werden als strukturierte JSON-Antwort mit HTTP 503 und `Retry-After` ausgegeben.
- Der Browser wiederholt eine fehlgeschlagene Seite nach 15, 30 und 60 Sekunden.
- Suchfortschritt, Cursor, Ergebnisse und Diagnosedaten werden nach jeder Seite in IndexedDB gespeichert.
- Eine unterbrochene Suche kann ab der letzten noch offenen Seite fortgesetzt werden.
- Beim Fortsetzen nach Erreichen eines Seitenziels wird das Seitenbudget um den neu gewählten Umfang erweitert.
- Geladene Ergebnisse werden über Anzeigen-ID dedupliziert.
- Die Konsistenzprüfung kontrolliert pro Seite und kumuliert: abgerufen = eindeutig + Duplikate + ausgeblendet.
- Nur 80 Karten werden gleichzeitig gerendert; weitere Ergebnisse werden in 80er-Schritten eingeblendet.
- Worker, Oberfläche und PWA-Cache verwenden Version 0.40.
