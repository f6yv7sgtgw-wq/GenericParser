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

## 0.44.5 – Free-Runtime-Hardening – CPU-Ziel erreicht

Im Live-Test bestätigt:

- direkter `WorkerEntrypoint` statt ASGI/FastAPI
- kein dynamischer Paket-Bootstrap
- kein Pydantic und kein `httpx` im Live-Pfad
- externer Abruf über Cloudflares `workers.fetch`
- erfolgreiche Suchaufrufe ohne `CpuLimitExceeded` oder Cloudflare 1101

Die erste direkte Runtime erkannte jedoch keine Karten und wurde deshalb nicht Referenz.

## 0.44.5.1 – Extraktionshotfix – Karten wiederhergestellt

Der Live-Test bestätigte:

- Link-Fallback erkennt wieder Anzeigenkarten
- 29 eindeutige SNES-Ergebnisse wurden geladen
- sechs Requests antworteten mit HTTP 200
- kein CPU-Limit- oder 1101-Fehler
- Ampel und Titelanzeige funktionieren

Dabei wurden drei Folgeprobleme sichtbar:

- Abbruch durch `pagination_repeated_page`, weil der Client die echte Weiter-URL nicht mitsendete
- sämtliche Preise blieben offen
- das Eventlog enthielt trotz Worker-Diagnose 0 Diagnoseblöcke

0.44.5.1 bleibt daher ein erfolgreicher Runtime- und Extraktionszwischenstand.

## 0.44.5.2 – Pagination-, Preis- und Diagnosehotfix – implementiert, Live-Test ausstehend

Ziel: Den direkten Free-Worker und die funktionierende Kartenextraktion behalten und die drei Befunde aus 0.44.5.1 schließen.

Umgesetzt:

- die vom Worker gefundene Kleinanzeigen-`Weiter`-URL wird im Browser pro Suchlauf und virtuellem Arbeitsschritt gespeichert
- Folgeanfragen senden diese URL unverändert als `cursor_url`
- beim Ende einer physischen Ergebnisseite springt der virtuelle Index auf den Beginn des nächsten Vier-Paket-Blocks
- der Wiederholungsseiten-Guard bleibt als Sicherheitsnetz erhalten
- Link-Fallback bevorzugt den vollständigen `li.ad-listitem`- oder `article`-Container statt eines zu kleinen inneren `div`
- reine Navigationskandidaten werden vor der Paketbildung entfernt
- Preise werden aus alter Preis-Klasse, explizitem Euro-Text oder strukturiertem `data-price` gewonnen
- bei nachträglich erkanntem Preis wird die aktive Ampelbewertung erneut berechnet
- jeder erfolgreiche Arbeitsschritt schreibt ein Ereignis `coverage_diagnostics` in das Eventlog
- Diagnose enthält Kandidaten, entfernte Navigation, erkannte/fehlende Preise, Quell-URL, Cursor, Cursor-Übergang und zurückgegebene IDs
- direkter Worker ohne ASGI, FastAPI, Pydantic, `httpx` oder dynamischen Paket-Bootstrap bleibt bestehen

Abnahmetest nach Deployment:

1. `/api/version` muss 0.44.5.2 und `direct-stdlib-cursor-price-diagnostics-v1` melden.
2. Eine Suche nach `Snes` muss über den ersten physischen Ergebnissatz hinaus neue IDs laden.
3. Der Payload nach einem Seitenübergang muss `cursor_url` enthalten.
4. `pagination_repeated_page` darf nicht bereits nach dem ersten Ergebnisseitenblock auftreten.
5. Angebotskarten mit Euro-Preis müssen einen numerischen Preis zeigen.
6. Das Eventlog muss mindestens einen `coverage_diagnostics`-Block pro erfolgreichem Request enthalten.
7. Mindestens 50 Arbeitspakete und 300 Ergebnisse ohne `CpuLimitExceeded` oder Cloudflare 1101 verarbeiten.
8. Manuellen Stopp, Fortsetzen und Datenkonsistenz prüfen.

Erst nach bestandenem Live-Test wird 0.44.5.2 operative Referenz. Danach beginnt 0.45.

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
