# Roadmap

## Leitlinie

Kleinanzeigen wird vollständig und belastbar umgesetzt, bevor eine zweite Quelle begonnen wird. Jede Phase muss durch Tests und reale Suchläufe abgesichert sein.

## Version 0.1 – Bibliothekskern

- Python-Paketstruktur
- Datenmodelle für SearchProfile, Listing und MatchResult
- Konfigurationsschema
- Text-, Preis-, Datums- und Ortsnormalisierung
- öffentliche Service-Schnittstelle
- Unit-Tests für Normalisierungs-Sonderfälle
- Beispielprofile für die spätere Einbindung

**Abnahme:** Modelle und Normalisierung funktionieren unabhängig von einem Live-Zugriff auf Kleinanzeigen.

## Version 0.2 – Kleinanzeigen-Ergebnislisten

- URL-Erzeugung für Keyword- und Kategoriesuche
- Location-ID-Verwaltung und Verifikation
- sequenzieller HTTP-Client
- Parsing der Ergebniskarten
- Erkennung von Nulltreffer, Layoutwechsel und Blockierung
- Deduplizierung doppelter TOP-Anzeigen
- gespeicherte HTML-Fixtures für reproduzierbare Tests

**Abnahme:** Echte und gespeicherte Ergebnislisten werden konsistent in Listing-Objekte umgewandelt.

## Version 0.3 – Matching und Scoring

- Normalisierung von Titel und Beschreibung
- Modellnummern- und Schreibvarianten-Matching
- Gesuch-, Stellenanzeigen-, Zubehör- und Defektfilter
- Negationsbehandlung für Begriffe wie „nicht defekt“
- Konvolut-Erkennung als eigene Trefferklasse
- nachvollziehbares Score- und Begründungsmodell

**Abnahme:** Die fachlichen Positiv- und Negativbeispiele aus der Spezifikation bestehen automatisiert und an realen Anzeigen.

## Version 0.4 – Detailseiten und Persistenz

- selektives Laden von Detailseiten im Graubereich
- SQLite für gesehene Anzeigen, Alerts und Preisverlauf
- Baseline-Lauf ohne Alert-Flut
- erneute Bewertung bei Preissenkungen
- Trennung von gesehen und erfolgreich verarbeitet
- kontrollierte Retries, Backoff und Rate-Limiting

**Abnahme:** Mehrere Läufe erzeugen keine Doppelmeldungen; fehlgeschlagene Verarbeitung verliert keine Treffer.

## Version 0.5 – Integration Evercade

- Adapter im Evercade-Projekt
- Suchprofile aus fehlenden beziehungsweise überwachten Cartridges
- Übergabe von Preislimits und Richtwerten
- Anzeige der Match-Begründung
- realer Parallelbetrieb mit Feedback zu Fehlalarmen

**Abnahme:** Evercade kann GenericParser als Bibliothek nutzen, ohne Parsercode zu duplizieren.

## Version 0.6 – Integration SNES

- Adapter im SNES-PAL-Sammlung-Projekt
- Suchprofile für SNES-PAL-Titel und Schreibvarianten
- Nutzung derselben Bibliotheks-API
- Vergleich der Anforderungen beider Projekte
- Beseitigung verbleibender projektspezifischer Annahmen

**Abnahme:** Beide Projekte verwenden denselben Parserkern und unterscheiden sich nur in Konfiguration und Ergebnisverarbeitung.

## Version 0.7 – Betriebsstabilität

- längerer Realbetrieb
- Parser-Metriken und Diagnoseausgaben
- Wartungsalarm bei Layoutänderung
- Kalibrierung von Scores und Schwellenwerten
- dokumentierter Umgang mit Blockierungen
- vollständiger Abnahmetest mit konkreten Anzeigen

**Abnahme:** Stabiler Kleinanzeigen-Betrieb mit nachvollziehbarer Trefferqualität und ohne unbemerkte Totalausfälle.

## Version 1.0 – Kleinanzeigen stabil

- dokumentierte öffentliche API
- Migrations- und Integrationsanleitung
- vollständige Testsuite
- reproduzierbare Releases
- beide Zielprojekte produktiv angebunden
- offene bekannte Einschränkungen dokumentiert

## Nach Version 1.0

Erst jetzt wird anhand der Erfahrungen entschieden, ob als nächste Quelle eBay, Vinted oder eine andere Plattform sinnvoll ist. Die bestehende Architektur wird nicht vorsorglich auf deren vermutete Anforderungen zugeschnitten.
