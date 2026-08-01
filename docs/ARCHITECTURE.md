# Architektur

## 1. Zielbild

GenericParser ist eine eigenständige Python-Bibliothek für Kleinanzeigen. Sie soll von mehreren Anwendungen eingebunden werden können, ohne deren Fachlogik zu kennen.

Die erste produktive Nutzung erfolgt in:

- Evercade
- SNES-PAL-Sammlung

Beide Projekte konfigurieren Suchprofile und verarbeiten Treffer. GenericParser übernimmt Suche, Parsing, Normalisierung, Matching, Bewertung und technische Persistenz.

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
- technische Zustände und Parse-Fehler melden
- später Produktkandidaten matchen und bewerten
- später Duplikate, Preisänderungen und Alerts dauerhaft speichern

### Evercade und SNES

- Produktkataloge und Sammlungsstatus verwalten
- Suchprofile aus fehlenden oder überwachten Spielen erzeugen
- Preislimits und Richtwerte bereitstellen
- Treffer darstellen oder Benachrichtigungen auslösen
- Nutzerfeedback verwalten

## 4. Öffentliche Bibliotheksschnittstelle

```python
from generic_parser import GenericParser, KleinanzeigenAdapter, KleinanzeigenHttpClient

with KleinanzeigenHttpClient() as http:
    parser = GenericParser(source=KleinanzeigenAdapter(http=http))
    listings = parser.search(profile)
```

Der Adapter erfüllt das `ListingSource`-Protokoll und liefert ausschließlich normalisierte `Listing`-Objekte.

## 5. Kleinanzeigen-Listenadapter seit 0.2a

Der Adapter besteht aus vier getrennten Bausteinen:

- `KleinanzeigenUrlBuilder` für Keyword- und Kategorie-URLs
- `KleinanzeigenHttpClient` für sequenzielle, gedrosselte Abrufe
- `KleinanzeigenPageParser` für robuste Kartenextraktion und Diagnosezustände
- `KleinanzeigenAdapter` als Implementierung des öffentlichen `ListingSource`-Ports

Netzwerk und Parsing sind getrennt. Tests können deshalb Mock-Antworten und gespeicherte HTML-Fixtures nutzen.

## 6. Diagnose-Webinterface seit 0.2b

Das Webinterface ist eine dünne FastAPI-Schicht über dem Parserkern. Es enthält keine eigene Parsinglogik. Die Oberfläche unterstützt drei Testmodi:

- gespeicherte Paket-Fixtures
- manuell eingefügtes HTML
- kontrollierte Live-Suche über den Kleinanzeigen-HTTP-Client

Live-Suchen sind innerhalb einer Instanz serialisiert. Die API erzeugt ausschließlich Kleinanzeigen-URLs über den `KleinanzeigenUrlBuilder`; frei wählbare Remote-URLs werden nicht abgerufen. Gespeicherte Fixtures werden in einem konfigurierbaren Datenverzeichnis abgelegt.

Die Weboberfläche ist ein Diagnosewerkzeug. Produktentscheidungen, Datenbankzustände und Hintergrundplanung bleiben späteren Komponenten vorbehalten.

## 7. Integrationsprinzip

GenericParser darf Evercade oder SNES nicht importieren. Die Abhängigkeit zeigt ausschließlich in die andere Richtung:

```text
Evercade ---------> GenericParser
SNES-PAL-Sammlung -> GenericParser
```

Treffer werden als Datenobjekte zurückgegeben. Darstellung und Benachrichtigung bleiben in den aufrufenden Projekten.

## 8. Späterer Hintergrundbetrieb

Ab der Persistenz- und Betriebsphase wird GenericParser als zentraler Worker mit kleiner API betrieben. Evercade und SNES teilen sich dann denselben Kleinanzeigen-Zugriff, dieselbe Datenbank und dasselbe Rate-Limit-Budget.

## 9. Stand 0.2c – Cloudflare Mobile

Die Cloud-Version ist eine zusätzliche, bewusst begrenzte Laufzeit:

```text
Smartphone → PWA / Workers Static Assets → FastAPI Python Worker → Kleinanzeigen
```

Der Worker führt pro Anfrage nur eine Keyword-Suche aus. Netzwerkzugriff erfolgt asynchron; der HTML-Parser baut nur die relevanten Anzeigenkarten auf. Die PWA enthält keine Parserlogik und speichert lediglich ein optionales Zugriffstoken im lokalen Browser. Hintergrundläufe, Persistenz und Benachrichtigungen bleiben der späteren Worker-Phase vorbehalten.
