# GenericParser Roadmap

## Funktionale Referenz 0.44.4

0.44.4 bleibt die fachliche Vergleichsbasis für:

- stabilen Suchstart und manuellen Stopp
- 7er-Arbeitspakete mit 5 Sekunden Pause
- echte Kleinanzeigen-Weiter-Navigation
- robuste Titel- und Kartenextraktion
- gespeicherten Fortschritt und Fortsetzen
- Datenkonsistenz
- Ampelbewertung ausschließlich aktiver Regeln
- kompakte Ergebniskarten

Der Live-Test vom 04.08.2026 bestätigte Fachlogik und Datenkonsistenz. Ein langer Lauf wurde nach 37 erfolgreichen Anfragen und 248 gespeicherten Ergebnissen durch `Python Worker exceeded CPU time limit` beendet. Deshalb ist 0.44.4 die funktionale, aber nicht uneingeschränkt operative Referenz.

## 0.44.5 bis 0.44.5.2 – experimentelle Runtime-Linie

Die direkte Standardbibliothek-Runtime beseitigte den beobachteten Import-/ASGI-Fehler in kurzen Testläufen, erreichte aber nicht die funktionale Abdeckung der Referenz:

- 0.44.5: keine Karten erkannt
- 0.44.5.1: Karten wieder erkannt, aber nur 29 Ergebnisse und keine Preise
- 0.44.5.2: Preise und Diagnose verbessert, Pagination weiterhin nach 29 Ergebnissen beendet

Diese Linie ist als Experiment dokumentiert und wird nicht als Grundlage der Produkt-Roadmap verwendet.

## 0.44.6 – Funktionaler Rückbau auf 0.44.4 – implementiert, Live-Test ausstehend

Ziel: Die funktionale Qualität der Referenz vollständig wiederherstellen, bevor das integrationsfähige Modul entsteht.

Umgesetzt:

- `search_service_v0446` delegiert Suchfluss, Extraktion, Pagination, Diagnose und Ampellogik unverändert an 0.44.4
- keine Nutzung der Parser- und Cursorlogik aus 0.44.5.x
- Controller wieder als Identitäts-Wrapper um den bewährten `controller-0411`-Ablauf
- UI, Eventlog und Metadaten konsistent auf 0.44.6
- ASGI/FastAPI-Pfad der Referenz wiederhergestellt
- 0.44.5.x-Dateien bleiben nur zur Historie im Repository

Wichtige Einschränkung:

- 0.44.6 priorisiert die vollständige Suche
- das bekannte mögliche Python-Import-CPU-Limit des Free-Tarifs gilt noch als offenes Betriebsrisiko
- 0.44.6 behauptet nicht, dieses Laufzeitproblem bereits gelöst zu haben

Abnahmetest nach Deployment:

1. `/api/version` meldet 0.44.6 und Referenz 0.44.4.
2. Eine identische SNES- oder Evercade-Suche liefert dieselbe erste Ergebnismenge wie 0.44.4.
3. Nach dem ersten Ergebnissatz werden über den echten Weiter-Link neue IDs geladen.
4. Mindestens 20 Arbeitspakete und 100 eindeutige Ergebnisse prüfen.
5. Manuellen Stopp und Fortsetzen testen.
6. Datenkonsistenz muss durchgehend bestätigt bleiben.
7. Cloudflare-Logs auf `CpuLimitExceeded` beobachten.

Nach erfolgreichem Funktionstest wird 0.44.6 die neue Arbeitsreferenz. Das Runtime-Risiko wird anschließend isoliert behandelt, ohne den Referenzparser erneut zu ersetzen.

## 0.45 – Integrierbares Parser-Core-Modul

Ziel: Die bewährte Funktionalität als wiederverwendbares Modul für Evercade, SNES und weitere Projekte kapseln.

- UI-unabhängiger Parser-Core
- stabile Eingabe- und Ergebnisdatentypen
- projektneutrales Suchprofil
- Ampelbewertung als eigenständige Funktion
- JSON-Serialisierung für andere Projekte
- Adapter für Cloudflare Worker und lokale Tests
- unveränderter API-Vertrag für bestehende Clients

## 0.46 – Produktklassifizierung

- Hauptprodukt, Zubehör, Ersatzteil, Bundle, Gesuch, Vermietung und Service unterscheiden
- Zubehör-vs.-Hauptprodukt robuster erkennen
- projektspezifische Klassifikationsregeln zulassen
- Fehlklassifikationen aus Thule-, Evercade- und SNES-Testläufen als Regressionstests aufnehmen

## 0.47 – Cartridge-Normalisierung

- Evercade-Cartridge-Namen und Schreibvarianten vereinheitlichen
- SNES-PAL-Titel und Varianten normalisieren
- Einzelmodule aus Bundles erkennen
- Dubletten über unterschiedliche Titel hinweg zusammenführen

## 0.48 – Projektintegration

- stabile Suchschnittstelle für Evercade und SNES
- gespeicherte Suchprofile pro fehlender Cartridge
- Übergabe von Treffern, Ampel, Deal-Score und Angebotsdaten
- Rückmeldung gekauft, ignoriert oder bereits vorhanden

## 0.49 – Deal Engine

- Preis gegen Richtwert und Maximalpreis bewerten
- Zustand, Vollständigkeit und Versand berücksichtigen
- Deal-Klassen: sehr gut, interessant, prüfen, unpassend
- Gesamtpreis inklusive Versand berechnen

## 0.50 – Automatische Deal-Suche

- zeitgesteuerte Suche im Hintergrund
- nur neue oder geänderte Angebote melden
- Ergebnisverlauf und Preisänderungen speichern
- Integration in Evercade- und SNES-Benachrichtigungen

## 0.51 – Betrieb und Qualität

- feste Regressionstests für Pagination, Extraktion, Klassifizierung und Ampel
- feste Beispielsuchen für Evercade und SNES
- kompakte Betriebsdiagnose
- Release- und Deployment-Checkliste
