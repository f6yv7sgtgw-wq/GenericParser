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
- automatischer HTTP-Retry aktiv

Am Ende lieferte der Abruf für Seite 29 wiederholt eine HTML-Fehlerseite mit HTTP 503. Das war kein Paginationfehler und kein Versionskonflikt. Der Suchstand blieb gespeichert und konnte manuell fortgesetzt werden.

## 0.44.6.1 – Diagnosefix – Live-Test bestanden

Der Test bestätigte:

- Eventlog und Worker melden konsistent `0.44.6.1` / `gp-04461-20260804-1`
- Referenzmodus 0.44.4 wird korrekt erkannt
- HTML-503 wird verständlich als temporärer Abruffehler dargestellt
- ältere Ereignisse werden übernommen
- Suchkern, Trefferkarten, Preise und Ampel funktionieren unverändert

Der Lauf verarbeitete neun Arbeitspakete und speicherte 60 Ergebnisse. Danach folgte die bestätigte Fehlerkette:

```text
HTTP 503 mit HTML
→ unmittelbarer Retry
→ Cloudflare 1101 vor ASGI
→ retry_exhausted
→ Stand gespeichert, manuelles Fortsetzen möglich
```

Die bisherige Implementierung nahm eine Suche nach `retry_exhausted` bewusst nicht automatisch wieder auf. Sie bot nur die gespeicherte manuelle Fortsetzung an.

## 0.44.6.2 – Einmalige automatische Fortsetzung – implementiert, Live-Test ausstehend

Ziel: Die bestehende gespeicherte Suche nach der bestätigten 503/1101-Kette einmal automatisch fortsetzen, ohne Parser, Pagination oder Worker-Suchkern zu verändern.

Controller-Ablauf:

```text
retry_exhausted mit 1101 oder wiederholtem HTML-503
→ Suchstand bleibt gespeichert
→ 90 Sekunden Ruhezeit
→ /api/version mit Cache-Bypass prüfen
→ Version, Build und API-Vertrag müssen übereinstimmen
→ vorhandene „Letzte Suche fortsetzen“-Funktion einmal automatisch auslösen
→ bei erneutem Terminalfehler nur noch manuelles Fortsetzen
```

Umgesetzt:

- Recovery-Modul `auto-resume-04462.js` beobachtet die bestehenden Eventlog-Ereignisse
- Trigger nur bei `search_end` mit `retry_exhausted` und belastbarem 1101-/503-Nachweis
- 90 Sekunden Ruhezeit vor der ersten Bereitschaftsprüfung
- bis zu vier `/api/version`-Prüfungen im Abstand von 15 Sekunden
- genau ein automatischer Resume-Versuch je Suchkette
- kein unbegrenzter Retry- oder Resume-Kreis
- manueller Resume überschreibt die wartende Automatik
- Löschen des Suchstands löscht auch den Recovery-Zustand
- Recovery-Zustand bleibt bei einem Seiten-Reload höchstens 30 Minuten erhalten
- Eventlog protokolliert Planung, Health-Prüfung, Start, laufende Session, Abschluss und manuellen Fallback
- `search_service_v04462` delegiert direkt an den unveränderten 0.44.4-Kern
- Paketgröße bleibt 7 und normale Pause bleibt 5 Sekunden

Wichtige Grenze:

- Cloudflare garantiert nicht, dass die Bereitschaftsprüfung eine neue Worker-Instanz erzeugt
- 0.44.6.2 testet diese Recovery-Hypothese im Live-Betrieb
- das zugrunde liegende ASGI-/Import-Risiko wird nicht als behoben bezeichnet

Abnahmetest nach Deployment:

1. `/api/version` meldet 0.44.6.2 und den Recovery-Modus.
2. Normale Treffer und Pagination entsprechen 0.44.6.1.
3. Bei einer 1101-/503-Unterbrechung erscheint `auto_resume_scheduled` im Eventlog.
4. Die UI zählt 90 Sekunden herunter und prüft anschließend den Worker.
5. Nach erfolgreicher Prüfung erscheint `auto_resume_start`.
6. Die neue Session setzt auf der gespeicherten Seite fort und beginnt nicht bei Seite 1.
7. Bereits geladene Anzeigen werden nicht erneut als neue Ergebnisse gezählt.
8. Bei einem zweiten Terminalfehler erfolgt kein zweiter automatischer Resume; der manuelle Button bleibt verfügbar.
9. Manueller Stopp, manuelles Fortsetzen und Datenkonsistenz bleiben unverändert.

Bei erfolgreichem Test wird 0.44.6.2 operative Referenzkandidatin. Bei Fehlschlag bleibt 0.44.6.1 die Arbeitsreferenz; die Recovery wird dann als zustandsbehafteter Bestandteil von 0.45 umgesetzt.

## 0.45 – Integrierbares Parser-Core-Modul

Ziel: Die bewährte Funktionalität als wiederverwendbares Modul für Evercade, SNES und weitere Projekte kapseln.

- UI-unabhängiger Parser-Core
- stabile Eingabe- und Ergebnisdatentypen
- projektneutrales Suchprofil
- Ampelbewertung als eigenständige Funktion
- JSON-Serialisierung für andere Projekte
- Adapter für Cloudflare Worker und lokale Tests
- unveränderter API-Vertrag für bestehende Clients
- zustandsbehaftete Recovery-Schnittstelle, falls 0.44.6.2 nicht ausreichend stabil ist

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
