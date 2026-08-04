# GenericParser Roadmap

## Fachlicher Referenzkern 0.44.4

0.44.4 bleibt die fachliche Vergleichsbasis für Suchfluss, echte Kleinanzeigen-Weiter-Navigation, robuste Extraktion, Datenkonsistenz und die Ampelbewertung ausschließlich aktiver Regeln. Der Kern wird in den späteren 0.44.6.x-Versionen unverändert über `search_service_v0444` verwendet.

## Arbeitsreferenz 0.44.6.2

0.44.6.2 ist die bestätigte Arbeitsreferenz. Der Live-Test erreichte 34 erfolgreiche Arbeitspakete und 219 gespeicherte Ergebnisse, bevor eine Kette aus mehreren HTML-503-Antworten und Cloudflare 1101 vor ASGI auftrat. Suchstand, Treffer, Preise, Bilder, Ampeln, Pagination und Datenkonsistenz blieben erhalten. Die einmalige automatische Recovery wurde korrekt geplant.

## 0.44.6.3 – Recovery-Hardening – implementiert, Live-Test ausstehend

0.44.6.3 verändert nicht den Suchkern. Die Version verbessert ausschließlich die Recovery-Steuerung.

Umgesetzt:

- neuer `GET /api/recovery-probe`
- Probe lädt Python-Runtime und Search-Service und validiert `SearchRequest`, `search_page` und den Referenzkern `generic_parser.search_service_v0444`
- keine Kleinanzeigen-Anfrage innerhalb der Probe
- Recovery-Trigger für Cloudflare 1101, 1102 und wiederholte HTML-503-Antworten
- gestaffeltes Backoff von 90, 180 und 360 Sekunden
- ±10 Prozent Jitter
- Probe-Abstände von 30, 60 und 120 Sekunden
- höchstens drei Probe-Versuche je Recovery-Zyklus
- höchstens zwei automatische Fortsetzungen je Suchkette
- danach ausschließlich manuelle Fortsetzung
- Auswertung von `cf-error-type`, `cf-error-origin`, `Retry-After` und Ray-ID
- sichtbare Recovery-Kachel mit Status, Versuchen, nächster Aktion und letzter Probe
- persistenter Recovery-Stand über einen Seiten-Reload
- keine unbegrenzte Retry- oder Resume-Schleife

Unverändert:

- 7er-Arbeitspakete
- 5 Sekunden normale Pause
- Suchlogik aus 0.44.4
- Pagination und Weiter-Link
- Titel-, Karten- und Preisextraktion
- Ampelbewertung
- Deduplizierung
- Speichern, Stoppen und manuelles Fortsetzen

Abnahmetest:

1. `/api/version` meldet 0.44.6.3 und den Recovery-Hardening-Vertrag.
2. `/api/recovery-probe` liefert `status: ready` und bestätigt den Referenzkern.
3. Normale Treffer und Pagination entsprechen 0.44.6.2.
4. Nach einem Terminalfehler erscheint `recovery_scheduled`.
5. Der erste Zyklus wartet ungefähr 90 Sekunden, der zweite ungefähr 180 Sekunden; jeweils mit ±10 Prozent Jitter.
6. Nach erfolgreicher Probe erscheinen `recovery_probe_ready`, `recovery_resume_start` und `recovery_resume_running`.
7. Die Fortsetzung startet auf der gespeicherten Seite und erzeugt keine neuen Dubletten.
8. Nach zwei gescheiterten automatischen Fortsetzungen bleibt ausschließlich die manuelle Fortsetzung verfügbar.
9. Datenkonsistenz muss durchgehend bestätigt bleiben.

Nach bestandenem Live-Test wird 0.44.6.3 operative Referenz. Danach geht die Entwicklung zurück in die Produkt-Roadmap.

## 0.45 – Integrierbares Parser-Core-Modul

- UI-unabhängiger Parser-Core
- stabile Ein- und Ergebnisdatentypen
- projektneutrale Suchprofile
- Ampelbewertung als eigenständige Funktion
- JSON-Schnittstelle für andere Projekte
- Adapter für Cloudflare, Evercade und SNES
- Recovery-Schnittstelle für gespeicherte Suchaufträge

## 0.46 – Produktklassifizierung

- Hauptprodukt, Zubehör, Ersatzteil, Bundle, Gesuch, Vermietung und Service unterscheiden
- projektspezifische Klassifikationsregeln
- Regressionstests aus Thule-, Evercade- und SNES-Suchen

## 0.47 – Cartridge-Normalisierung

- Evercade- und SNES-PAL-Titel vereinheitlichen
- Schreibvarianten, Nummern und Editionen normalisieren
- Einzelmodule aus Bundles erkennen

## 0.48 – Projektintegration

- Suchprofile pro fehlender Cartridge
- strukturierte Übergabe von Treffer, Ampel und Angebotsdaten
- Integration in Evercade- und SNES-Sammlungsmanager

## 0.49 – Deal Engine

- Preis gegen Richtwert und Maximalpreis
- Zustand, Vollständigkeit und Versand
- Deal-Klassen und Gesamtpreis

## 0.50 – Automatische Deal-Suche

- zeitgesteuerte Suche
- nur neue oder geänderte Angebote melden
- Ergebnis- und Preisverlauf
- Benachrichtigungen für Evercade und SNES

## 0.51 – Betrieb und Qualität

- feste Regressionstests
- Referenzsuchen für Evercade und SNES
- Betriebsdiagnose
- Release- und Deployment-Checkliste
