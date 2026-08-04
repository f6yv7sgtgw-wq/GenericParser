# GenericParser Roadmap

## Funktionale Referenz 0.44.4

0.44.4 bleibt die fachliche Vergleichsbasis für:

- stabilen Suchstart und manuellen Stopp
- Cloudflare-Free-Tarif-kompatible Arbeitspakete
- echte Kleinanzeigen-Weiter-Navigation
- vollständige Trefferabdeckung bis zum Plattformabbruch
- robuste Titelgewinnung
- gespeicherten Fortschritt und Fortsetzen
- Datenkonsistenz
- Ampelbewertung ausschließlich aktiver Regeln
- kompakte Ergebniskarten

Der Live-Test vom 04.08.2026 bestätigte Fachlogik und Datenkonsistenz. Ein langer Lauf wurde nach 37 erfolgreichen Anfragen und 248 gespeicherten Ergebnissen durch `Python Worker exceeded CPU time limit` beendet. Deshalb bleibt 0.44.4 die funktionale Vergleichsbasis.

## 0.44.5 – Free-Runtime-Hardening – CPU-Ziel erreicht, Extraktionsregression entdeckt

Umgesetzt und im Live-Test bestätigt:

- direkter `WorkerEntrypoint` statt ASGI/FastAPI
- kein dynamischer Paket-Bootstrap
- kein Pydantic und kein `httpx` im Live-Pfad
- externer Abruf über Cloudflares `workers.fetch`
- drei erfolgreiche HTTP-200-Suchaufrufe ohne `CpuLimitExceeded` oder Cloudflare 1101

Entdeckte Regression:

- Kleinanzeigen meldete bei der Suche `Snes` 6.669 Ergebnisse
- der direkte Parser erkannte 0 Karten
- die Suche endete fälschlich mit `empty_page_verified`

0.44.5 ist daher Runtime-Nachweis, aber keine operative Referenz.

## 0.44.5.1 – Extraktionshotfix – implementiert, Live-Test ausstehend

Ziel: Den schlanken direkten Worker aus 0.44.5 behalten und die Kartenextraktion wiederherstellen.

Umgesetzt:

- primäre Kartenfindung weiterhin über `article[data-adid]`
- zusätzlicher Fallback über eindeutige `/s-anzeige/`-Links
- Anzeigen-ID wird aus der Kleinanzeigen-URL gewonnen
- begrenzte Kartenfenster für `article`, `li.ad-listitem`, `div.aditem` und unbekannte Container
- gemeldete Treffer mit 0 erkannten Karten erzeugen einen strukturierten `ParserLayoutError` statt eines falschen Suchabschlusses
- `empty_page_verified` ist nur noch bei tatsächlich leerer Seite zulässig
- neues Diagnoseschema `direct-stdlib-link-fallback-v1`
- Diagnosewerte für Artikel-Tags, `data-adid`, Anzeigenlinks, eindeutige Links, Kandidatenzahl und Extraktionsstrategie
- direkter Worker, aktive Ampelregeln, 7er-Arbeitspakete und UI-Vertrag bleiben unverändert

Abnahmetest nach Deployment:

1. `/api/version` muss 0.44.5.1 und `direct-stdlib-link-fallback-v1` melden.
2. Eine Suche nach `Snes` muss im ersten Paket echte Karten liefern oder einen strukturierten Extraktionsfehler mit Diagnosewerten ausgeben.
3. `reportedTotal > 0` darf niemals mehr mit `empty_page_verified` enden.
4. Mindestens 50 Arbeitspakete und 300 Ergebnisse ohne `CpuLimitExceeded` oder Cloudflare 1101 verarbeiten.
5. Manuellen Stopp, Fortsetzen und Datenkonsistenz prüfen.

Erst nach bestandenem Live-Test wird 0.44.5.1 operative Referenz.

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
