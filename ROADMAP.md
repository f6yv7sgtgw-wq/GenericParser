# GenericParser Roadmap

## Fachlicher Referenzkern 0.44.4

0.44.4 bleibt die fachliche Vergleichsbasis für Suchfluss, echte Kleinanzeigen-Weiter-Navigation, robuste Extraktion, Datenkonsistenz und die Ampelbewertung ausschließlich aktiver Regeln. Der Kern wird unverändert über `search_service_v0444` verwendet.

## Stabile Rückfallreferenz 0.44.6.5

0.44.6.5 bleibt der bekannte operative Rückfallstand:

- bestätigter ASGI- und FastAPI-Pfad
- unveränderter 0.44.4-Suchkern
- 7er-Arbeitspakete
- fünf Sekunden Browserpause
- echte Weiter-Navigation
- persistente Fortschrittssicherung
- bestehendes einmaliges Auto-Resume-Verhalten

Die Recovery- und Cooldown-Experimente aus 0.44.6.3 bis 0.44.6.6.1 sind abgeschlossen und werden nicht in den aktiven 0.45-Suchpfad übernommen.

## 0.45.0 – Integrierbares Parsermodul

Status: **implementiert und GitHub-CI-bestätigt; Cloudflare-Live-Abnahme durch ungültigen Deployment-Token blockiert**.

Enthalten:

- versionierter Vertrag `generic-parser-module-v1`
- `ModuleSearchProfile` als projektneutrales Suchprofil
- einheitliche Listings, Pagination und Summary
- unveränderte Delegation an den 0.44.4-Suchkern
- kompatibler `/api/search`-Pfad für die bestehende Oberfläche
- neue Endpunkte unter `/api/module/v1/*`
- Evercade-Profiladapter
- SNES-PAL-Profiladapter
- Debug-Logs als expliziter, standardmäßig deaktivierter Schalter
- netzwerkfreie Modultests als expliziter, standardmäßig deaktivierter Schalter
- eigener CI-Workflow für Modulvertrag und Referenzschutz
- vollständiger API-, Funktions- und Free-Worker-Limitierungssnapshot
- verbindlicher Release-Prozess und strukturierte Metadaten für alle folgenden Releases
- allgemeiner Release-Integritätscheck ohne Pfadfilter
- livefähiger Deployment-Smoke-Test für Vertrag, Selbsttest und ein echtes 7er-Arbeitspaket

### Abnahmekriterien 0.45.0

1. `/api/version` meldet `0.45.0`, Build `gp-0450-20260805-1` und Modulvertrag v1.
2. Die bestehende UI-Suche entspricht funktional 0.44.6.5.
3. Leere optionale Profilfelder werden nicht an den Suchkern übertragen.
4. `/api/module/v1/profile/validate` liefert ein serialisierbares Profil und Legacy-Payload.
5. `/api/module/v1/search` liefert das gemeinsame Ergebnisformat.
6. Debug-Logs bleiben ohne Schalter vollständig aus.
7. Modultests bleiben ohne Schalter gesperrt.
8. Aktivierte Modultests verwenden kein Kleinanzeigen-Netzwerk.
9. Evercade- und SNES-PAL-Adapter erfüllen denselben Profilvertrag.
10. Bei einer Regression bleibt 0.44.6.5 sofort wiederherstellbar.
11. GitHub liefert für den finalen Commit einen erfolgreichen Release-Integritätsstatus.
12. Cloudflare deployt exakt diesen Stand und besteht den aktualisierten Live-Smoke-Test.

## 0.45.1 – Evercade-Integration

- GenericParser-Modul im Evercade-Projekt anbinden
- Cartridge-Daten in `ModuleSearchProfile` übersetzen
- Richtwert und Maximalpreis übergeben
- Ergebnisse, Ampel, URL, Preis und Zustand zurückführen
- projektspezifische Tests standardmäßig deaktivierbar halten
- bestehende Evercade-Suche erst nach Vergleichslauf ersetzen

## 0.45.2 – SNES-PAL-Integration

- GenericParser-Modul im SNES-Sammlungsmanager anbinden
- PAL-Titel, Varianten und Ausschlussbegriffe übertragen
- NTSC/Repro-Prüfung projektspezifisch ergänzen
- Ergebnisvertrag gegen reale SNES-Suchprofile testen

## 0.45.3 – Gemeinsame Integrationsabnahme

- identische Modulversion in Evercade und SNES
- Referenzprofile und Fixture-Ergebnisse
- Vertragskompatibilität und Fehlerdarstellung
- gemeinsame Debug- und Testschalter
- dokumentierter Rückfall je Projekt

## 0.46 – Produktklassifizierung

- Hauptprodukt, Zubehör, Ersatzteil, Bundle, Gesuch, Vermietung und Service unterscheiden
- projektspezifische Klassifikationsregeln
- Regressionstests aus Thule-, Evercade- und SNES-Suchen

## 0.47 – Cartridge-Normalisierung

- Evercade- und SNES-PAL-Titel vereinheitlichen
- Schreibvarianten, Nummern und Editionen normalisieren
- Einzelmodule aus Bundles erkennen

## 0.48 – Projektintegration ausbauen

- Suchprofile pro fehlender Cartridge
- strukturierte Übergabe von Treffer, Ampel und Angebotsdaten
- mehrere Quellen hinter dem gemeinsamen Modulvertrag vorbereiten

## 0.49 – Deal Engine

- Preis gegen Richtwert und Maximalpreis
- Zustand, Vollständigkeit und Versand
- Deal-Klassen und Gesamtpreis

## 0.50 – Serverseitige Suchaufträge

- Queue, Workflow oder Durable Object separat bewerten
- persistente Arbeitspakete statt Browser-Recovery
- nur neue oder geänderte Angebote melden
- Ergebnis- und Preisverlauf
- Benachrichtigungen für Evercade und SNES

## 0.51 – Betrieb und Qualität

- feste Regressionstests
- Referenzsuchen für Evercade und SNES
- Betriebsdiagnose
- Release- und Deployment-Checkliste
