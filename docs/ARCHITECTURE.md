# Architektur

## 1. Zielbild

GenericParser ist eine eigenständige Python-Bibliothek für Kleinanzeigen. Sie soll von mehreren Anwendungen eingebunden werden können, ohne deren Fachlogik zu kennen.

Die erste produktive Nutzung erfolgt in:

- Evercade
- SNES-PAL-Sammlung

Beide Projekte konfigurieren Suchprofile und verarbeiten Treffer. GenericParser übernimmt ausschließlich Suche, Parsing, Normalisierung, Matching, Bewertung und technische Persistenz.

## 2. Grundsatz: generische Domäne, eine Quelle

Das interne Datenmodell bleibt quellenneutral, damit spätere Erweiterungen möglich sind. Trotzdem wird zunächst ausschließlich ein Kleinanzeigen-Adapter implementiert und getestet.

Es wird ausdrücklich keine vorzeitige Mehrquellen-Abstraktion gebaut, die Kleinanzeigen-Komplexität versteckt oder verallgemeinert. Erst nach einer stabilen Version 1.0 wird geprüft, welche Schnittstellen sich tatsächlich für eBay, Vinted oder andere Quellen eignen.

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
- Nutzerfeedback wie gekauft, ignoriert oder Fehlalarm verwalten

## 4. Kernmodelle

### SearchProfile

Ein Suchprofil enthält unter anderem:

- stabile Profil-ID
- Anzeigename
- Marke, Serie oder Plattform
- Modell- und Schreibvarianten
- Such-Queries
- erforderliche Begriffe
- Ausschlussbegriffe
- maximale Preise
- optionalen Marktwert-Richtwert
- Standort, Radius und Versandpräferenz
- Regeln für Konvolute und unvollständige Angebote

### Listing

Eine normalisierte Anzeige enthält mindestens:

- Anzeigen-ID
- Titel
- Rohpreis und normalisierten Preis
- Preis-Flags
- absolute URL
- PLZ, Ort und optionale Entfernung
- Veröffentlichungszeitpunkt
- Beschreibung oder Beschreibungsanriss
- auslösende Query
- Zeitpunkt des ersten und letzten Sehens

### MatchResult

Das Ergebnis der Auswertung enthält:

- Anzeige
- Suchprofil
- Score
- Entscheidung
- gefundene positive Signale
- gefundene Ausschluss- oder Warnsignale
- nachvollziehbare Begründung
- Information, ob eine Detailseite benötigt wurde
- Information, ob ein neuer Alert zulässig ist

## 5. Öffentliche Schnittstelle

Die Bibliothek soll zwei Nutzungsformen anbieten:

### Eingebettet

```python
results = parser.search(profile)
```

Diese Form wird von Evercade und SNES verwendet.

### Diagnose-CLI

```bash
generic-parser run --config profile.yaml --dry-run
```

Die CLI dient Entwicklung, Abnahmetests, Parserdiagnose und manuellen Suchläufen. Sie ist nicht die primäre Integrationsform.

## 6. Verarbeitungspipeline

1. Suchprofil validieren
2. Location-ID laden oder ermitteln
3. Such-URLs erzeugen
4. Ergebnislisten sequenziell abrufen
5. Karten extrahieren und innerhalb des Laufs deduplizieren
6. Rohdaten normalisieren
7. günstige Ausschlussfilter anwenden
8. Kandidaten matchen und scoren
9. nur im Graubereich Detailseite laden
10. gegen gespeicherte Anzeigen und Preisverlauf prüfen
11. MatchResult zurückgeben
12. Alert erst nach bestätigter Verarbeitung als versendet markieren

## 7. Persistenz

SQLite speichert getrennt:

- gesehene Anzeigen
- verschickte Alerts
- Preisverlauf
- Suchprofil-Baselines
- technische Parserzustände

Die Bibliothek darf eine Anzeige nicht als alarmiert markieren, bevor das aufrufende Projekt die erfolgreiche Verarbeitung bestätigt hat.

## 8. Integrationsprinzip

GenericParser darf Evercade oder SNES nicht importieren. Die Abhängigkeit zeigt ausschließlich in die andere Richtung:

```text
Evercade ---------> GenericParser
SNES-PAL-Sammlung -> GenericParser
```

Treffer werden als Datenobjekte zurückgegeben. Benachrichtigungen werden über Callbacks, Events oder einen schmalen Consumer-Port angebunden, nicht fest in den Parser eingebaut.

## 9. Erweiterung um weitere Quellen

Vor Version 1.0 wird kein produktiver Adapter für andere Marktplätze begonnen. Nach erfolgreichem Kleinanzeigen-Betrieb wird anhand realer Gemeinsamkeiten entschieden, welche Teile abstrahiert werden können.

Eine spätere Quelle muss mindestens dieselben normalisierten Kernmodelle liefern, darf aber eigene Such-, Rate-Limit- und Parse-Strategien besitzen.
