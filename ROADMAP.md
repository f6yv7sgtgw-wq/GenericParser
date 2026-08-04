# GenericParser Roadmap

## Referenz 0.44.4

0.44.4 ist die fachliche Referenz für:

- stabilen Suchstart und manuellen Stopp
- Cloudflare-Free-Tarif-kompatible Arbeitspakete
- echte Kleinanzeigen-Weiter-Navigation
- vollständige Trefferabdeckung bis zum Plattformabbruch
- robuste Titelgewinnung
- gespeicherten Fortschritt und Fortsetzen
- Datenkonsistenz
- Ampelbewertung ausschließlich aktiver Regeln
- kompakte Ergebniskarten

Der Live-Test vom 04.08.2026 bestätigte die Fachlogik und Datenkonsistenz. Ein langer Lauf wurde nach 37 erfolgreichen Anfragen und 248 gespeicherten Ergebnissen durch `Python Worker exceeded CPU time limit` beendet. Der Trace zeigt den Abbruch beim Import vor ASGI und vor dem ausgehenden Kleinanzeigen-Aufruf. Deshalb ist 0.44.4 die funktionale, aber noch nicht die operative Runtime-Referenz.

## 0.44.5 – Free-Runtime-Hardening

Ziel: 0.44.4 unverändert fachlich erhalten und den Cloudflare-Free-Startpfad unter das CPU-Limit bringen.

- direkter `WorkerEntrypoint` statt ASGI/FastAPI im Cloudflare-Pfad
- kein Pydantic-Modellaufbau pro kaltem Isolat
- keine dynamische `importlib`-Paketinitialisierung
- statische, kleine Imports im Request-Pfad
- leichte JSON-Validierung ohne Änderung des API-Vertrags
- identische Suchantworten und Ampelresultate zu 0.44.4
- Cold-Start- und Wiederholungs-Test
- langer Regressionstest mit gespeichertem Fortschritt

Erfolgskriterium: Kein CPU-Abbruch vor dem ersten ausgehenden Fetch. Erst danach wird 0.44.5 operative Referenz.

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
- Fehlklassifikationen aus den Thule-, Evercade- und SNES-Testläufen als Regressionstests aufnehmen

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
