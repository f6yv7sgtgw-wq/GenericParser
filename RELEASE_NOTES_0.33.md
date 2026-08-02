# GenericParser 0.33

## Änderungen
- Pagination protokolliert geladene Seiten, Treffer pro Seite und neue IDs pro Seite.
- Der genaue Abbruchgrund wird in API und Weboberfläche angezeigt.
- Keine Abbruchbedingung bei einer kurzen Ergebnisseite.
- Abbruch nur bei leerer Seite, wiederholter Seite, keinen neuen IDs, Nutzerlimit oder Sicherheitsgrenze von 100 Seiten.
- Weboberfläche und Service-Worker-Cache auf 0.33 aktualisiert.

## Architektur
Transport, Parsing, Normalisierung, Matching und UI bleiben getrennt. Die Pagination-Diagnose ergänzt den Cloudflare-Adapter und verändert das neutrale Listing-Modell nicht.
