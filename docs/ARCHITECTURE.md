# Architektur

## 1. Zielbild

GenericParser ist eine eigenständige Python-Bibliothek für Kleinanzeigen. Sie soll von mehreren Anwendungen eingebunden werden können, ohne deren Fachlogik zu kennen.

Die erste produktive Nutzung erfolgt in:

- Evercade
- SNES-PAL-Sammlung

Beide Projekte konfigurieren Suchprofile und verarbeiten Treffer. GenericParser übernimmt ausschließlich Suche, Parsing, Normalisierung, Matching, Bewertung und technische Persistenz.

## 2. Grundsatz: generische Domäne, eine Quelle

Das interne Datenmodell bleibt quellenneutral, damit spätere Erweiterungen möglich sind. Trotzdem wird zunächst ausschließlich ein Kleinanzeigen-Adapter implementiert und getestet.

Es wird ausdrücklich keine vorzeitige Mehrquellen-Abstraktion gebaut. Erst nach einer stabilen Version 1.0 wird geprüft, welche Schnittstellen sich tatsächlich für eBay, Vinted oder andere Quellen eignen.

## 3. Verantwortlichkeiten

### GenericParser

- Such-URLs aus einem Suchprofil erzeugen
- Location-ID ermitteln, speichern und verifizieren
- Kleinanzeigen-Ergebnislisten sequenziell abrufen
- Anzeigenkarten robust extrahieren
- Preise, Datum, Ort und Entfernung normalisieren
- Titel und Beschreibung vereinheitlichen
- Gesuche, Stellenanzeigen, Zubehör und Defektware erkennen
- Produktkandidaten matchen und bewerten
- Duplikate sowie bereits bekannte Anzeigen erkennen
- Preisänderungen speichern und bewerten
- technische Zustände und Parse-Fehler melden
- normalisierte Ergebnisse über eine stabile API zurückgeben

### Evercade und SNES

- Produktkataloge und Sammlungsstatus verwalten
- Suchprofile aus fehlenden oder überwachten Spielen erzeugen
- Preislimits und Richtwerte bereitstellen
- Treffer darstellen oder Benachrichtigungen auslösen
- Nutzerfeedback verwalten

## 4. Öffentliche Schnittstelle in 0.1

```python
from generic_parser import GenericParser, SearchProfile

parser = GenericParser(source=source_adapter)
listings = parser.search(profile)
```

`source_adapter` erfüllt das `ListingSource`-Protokoll. Ab 0.2 stellt das Projekt dafür einen Kleinanzeigen-Adapter bereit.

## 5. Integrationsprinzip

GenericParser darf Evercade oder SNES nicht importieren. Die Abhängigkeit zeigt ausschließlich in die andere Richtung:

```text
Evercade ---------> GenericParser
SNES-PAL-Sammlung -> GenericParser
```

Treffer werden als Datenobjekte zurückgegeben. Darstellung und Benachrichtigung bleiben in den aufrufenden Projekten.

## 6. Späterer Hintergrundbetrieb

Ab der Persistenz- und Betriebsphase wird GenericParser als zentraler Worker mit kleiner API betrieben. Evercade und SNES teilen sich dann denselben Kleinanzeigen-Zugriff, dieselbe Datenbank und dasselbe Rate-Limit-Budget.
