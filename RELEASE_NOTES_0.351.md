# GenericParser 0.351

- `max_results` wird nur noch wirksam, wenn das Frontend zusätzlich `max_results_explicit: true` sendet.
- Safari-Wiederherstellung oder alte JavaScript-Stände können dadurch kein verstecktes Ergebnislimit mehr aktivieren.
- Das Feld „Max. Rohfunde“ wird beim Laden und bei `pageshow` zurückgesetzt.
- Gespeicherte Profile aktivieren ein Limit nur, wenn dort bewusst ein positiver Wert gespeichert wurde.
- Die Diagnose zeigt Ergebnislimit, Explizitstatus, Seitengröße, Seitenzahlen und Abbruchgrund.
- Worker, Weboberfläche und Service-Worker-Cache wurden auf 0.351 aktualisiert.
- Lokale Prüfung: 85 Tests bestanden, 1 optionaler Live-Test übersprungen.
