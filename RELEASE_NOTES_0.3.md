# GenericParser 0.3

## Matching und Scoring

- Modellnummern und Schreibvarianten werden normalisiert verglichen, einschließlich Leerzeichen-, Bindestrich- und einfacher römischer Nummernvarianten.
- Gesuche, Stellenanzeigen, Zubehör, Defektanzeigen und Konvolute werden als eigene Trefferklassen erkannt.
- Negationen wie „nicht defekt“ verhindern eine falsche Defektklassifizierung.
- Pflichtbegriffe, Ausschlussbegriffe, Marken, Modellmuster, Preislimit und Richtwert fließen nachvollziehbar in einen Score von 0 bis 100 ein.
- Ergebnisse werden als `alert`, `review` oder `reject` eingestuft und mit positiven Signalen, Warnungen und Begründung ausgegeben.

## Webinterface und API

- Filter und Sortierung nach Relevanz, Datum und Preis.
- Suchprofile werden lokal im Browser gespeichert und wieder geladen.
- Diagnose zeigt Rohfunde, sichtbare Treffer, Prüffälle, Ablehnungen und Duplikate.
- Die API liefert weiterhin normalisierte Listings; Matchingdaten ergänzen die Antwort.

## Architektur

Die ursprüngliche Schichtung bleibt erhalten: Kleinanzeigen-Transport und Parser liefern `Listing`-Objekte. Die neue Matching-Schicht arbeitet danach ausschließlich auf dem neutralen Modell. Evercade und SNES werden nicht importiert; weitere Quellen bleiben außerhalb von 0.3.

## Validierung

- 80 automatisierte Tests bestanden.
- 1 optionaler Live-Netzwerktest wurde planmäßig übersprungen.
