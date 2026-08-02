# GenericParser 0.37

## Transparente Grob- und Detailsuche

0.37 unterscheidet erstmals zwischen sehr breiten Suchbegriffen und gezielt eingegrenzten Suchen.

- Die Kleinanzeigen-Mobile-API wird auf der ersten Seite nach der gemeldeten Gesamtzahl ausgewertet.
- Ungefilterte Suchen mit mindestens 1.000 gemeldeten Treffern werden als breite Suche erkannt.
- Breite Suchen liefern einen klar gekennzeichneten Ausschnitt statt einer irreführenden Vollständigkeitsmeldung.
- Die Oberfläche zeigt die von Kleinanzeigen gemeldete Gesamtzahl und die tatsächlich geladene Menge getrennt an.
- Pflichtbegriffe, Ausschlussbegriffe, Modellvarianten, Marken, Preis, Ort, Radius oder ein explizites Ergebnislimit machen die Suche gezielt.
- Gezielte Suchen verwenden weiterhin die automatische Cursor-Fortsetzung aus 0.36.
- Der API-Vertrag wurde auf `match-v4-scope` erweitert.
- Worker, PWA und Service-Worker-Cache wurden auf 0.37 aktualisiert.

## Ziel

Eine Suche nach einem sehr allgemeinen Begriff wie `snes` mit mehreren Tausend Treffern wird nicht mehr so dargestellt, als seien einige Dutzend geladene Anzeigen das vollständige Ergebnis. Stattdessen wird der Suchumfang transparent ausgewiesen und eine Eingrenzung empfohlen.
