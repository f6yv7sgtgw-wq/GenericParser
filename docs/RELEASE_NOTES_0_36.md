# GenericParser 0.36

## Ziel

Große Kleinanzeigen-Suchen werden vollständig über mehrere ressourcensichere Worker-Anfragen geladen, statt innerhalb einer einzelnen Anfrage an Cloudflare-Grenzen zu stoßen.

## Änderungen

- neuer Cursor-Vertrag `match-v3-cursor`
- Mobile-API wird in Blöcken von höchstens vier Seiten verarbeitet
- HTML-Fallback wird in Blöcken von höchstens zwei Seiten verarbeitet
- jede Antwort enthält Quelle, Startseite, nächste Seite, Stop-Grund und Vollständigkeitsstatus
- die Oberfläche setzt unvollständige Blöcke automatisch fort
- Deduplizierung über alle Blöcke anhand der Anzeigen-ID
- ein bewusst gesetztes Ergebnislimit gilt für die zusammengeführte Gesamtliste
- bereits geladene Ergebnisse bleiben bei einem späteren Fehler sichtbar
- globale Sortierung der zusammengeführten Ergebnisliste
- Diagnose zeigt Anfragen, Seiten, Duplikate, Cursor und Blockstatus
- PWA- und Service-Worker-Cache auf 0.36 aktualisiert

## Ressourcenmodell

Eine einzelne Worker-Anfrage bleibt bewusst klein. Die Vollständigkeit entsteht durch mehrere sequenzielle Cursor-Anfragen im Browser. Dadurch wird das Cloudflare-Ressourcenlimit nicht durch eine lange Abrufschleife innerhalb eines Requests belastet.

## Datenkonsistenz

Jeder Worker-Block ist intern konsistent. Die Weboberfläche führt die Blöcke ausschließlich über eindeutige Anzeigen-IDs zusammen. Doppelte Anzeigen werden gezählt, aber nicht erneut dargestellt.
