# GenericParser 0.32

- Optionale Felder starten leer.
- Leere Felder werden nicht an die API gesendet und nicht ausgewertet.
- Ein leeres Feld „Max. Rohfunde“ bedeutet: alle verfügbaren Ergebnisse laden.
- Pagination läuft bis die Kleinanzeigen-API keine weitere volle Seite mehr liefert.
- Ergebnislisten werden nicht mehr durch das Frontend abgeschnitten.
- Service-Worker-Cache auf 0.32 angehoben.

## Validierung

- 84 Tests bestanden.
- 1 optionaler Live-Test planmäßig übersprungen.
- Architektur bleibt getrennt: Transport → Parser → Listing → Matching → API/UI.
