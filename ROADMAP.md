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

## 0.44.6 – Funktionaler Rückbau auf 0.44.4 – Live-Test bestanden

Der Live-Test bestätigte die Wiederherstellung der funktionalen Qualität:

- 184 eindeutige Ergebnisse gespeichert
- mindestens 29 Arbeitspakete erfolgreich verarbeitet
- echte Weiter-Navigation über den Referenzkern
- Preise, Bilder und Ampelbewertungen vorhanden
- Suchstand bei temporärem Fehler erhalten
- automatischer Retry aktiv

Am Ende lieferte der Abruf für Seite 29 wiederholt eine HTML-Fehlerseite mit HTTP 503. Das war kein Paginationfehler und kein Versionskonflikt. Der Suchstand blieb gespeichert und konnte fortgesetzt werden.

Das Eventlog zeigte fälschlich `Versionsabweichung`, obwohl UI und Worker bei Version, Build und API-Vertrag übereinstimmten. Ursache war die zusätzliche Erwartung eines experimentellen Diagnoseschemas, das im Referenzmodus bewusst nicht geliefert wird.

## 0.44.6.1 – Diagnosefix – implementiert, Live-Test ausstehend

0.44.6.1 verändert ausschließlich Diagnose und Versionsdarstellung:

- Versionskonsistenz wird nur anhand von Version, Build und API-Vertrag geprüft
- fehlendes erweitertes Diagnoseschema wird im Referenzmodus nicht als Fehler bewertet
- Anzeige: `Referenz 0.44.4 · erweitertes Schema optional`
- HTML-Antworten mit HTTP 503 werden als temporärer Cloudflare-/Upstream-Abruffehler bezeichnet
- Hinweis, dass der Suchstand erhalten bleibt und Retry oder Fortsetzen möglich ist
- Anzahl temporärer HTML-503-Antworten erscheint in der Eventlog-Zusammenfassung
- Suchfluss, Extraktion, Pagination, Ampel, Arbeitspakete und Retry-Verhalten bleiben unverändert
- `search_service_v04461` delegiert direkt an den unveränderten 0.44.4-Kern

Abnahmetest nach Deployment:

1. `/api/version` meldet 0.44.6.1, Build `gp-04461-20260804-1` und Referenzmodus.
2. Eventlog zeigt `Versionen konsistent`.
3. Das fehlende Coverage-Schema wird als optionaler Referenzmodus dargestellt.
4. Ein vorhandenes HTML-503-Ereignis wird verständlich als temporärer Abruffehler angezeigt.
5. Eine identische Suche liefert dieselben Treffer und dieselbe Pagination wie 0.44.6.
6. Manueller Stopp, Retry, Fortsetzen und Datenkonsistenz bleiben unverändert.

Nach bestandenem Test wird 0.44.6.1 die neue Arbeitsreferenz. Anschließend beginnt 0.45.

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
