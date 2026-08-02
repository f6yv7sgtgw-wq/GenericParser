# GenericParser 0.39.1

Hotfix für fälschlich leere Suchergebnisse auf der ersten Mobile-API-Seite.

## Änderungen

- Eine leere oder nicht parsebare Mobile-API-Antwort auf Seite 1 wird nicht mehr sofort als vollständige Nulltreffersuche behandelt.
- Seite 1 wird automatisch über den HTML-Fallback gegengeprüft.
- Nur wenn Mobile-API und HTML-Fallback keine gültigen Treffer liefern, endet die Suche mit `empty_page_verified`.
- Die Antwort enthält Mobile-Diagnosedaten: Ziel-URL, HTTP-Status, Antwortgröße, Rohkarten, geparste und gültige Treffer.
- Der verwendete Fallback-Grund wird transparent ausgegeben.
- Worker, Oberfläche und Service-Worker-Cache wurden auf 0.39.1 aktualisiert.
- Regressionstests decken den leeren Mobile-Erstseitenfall und die HTML-Gegenprüfung ab.
