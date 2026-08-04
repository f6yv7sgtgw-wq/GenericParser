# GenericParser Roadmap

## Fachlicher Referenzkern 0.44.4

0.44.4 bleibt die fachliche Vergleichsbasis für Suchfluss, echte Kleinanzeigen-Weiter-Navigation, robuste Extraktion, Datenkonsistenz und die Ampelbewertung ausschließlich aktiver Regeln. Der Kern wird weiterhin unverändert über `search_service_v0444` verwendet.

## Stabile Referenz 0.44.6.5

0.44.6.5 ist die stabile operative Rollback-Referenz. Sie verwendet:

- den bestätigten ASGI- und FastAPI-Pfad aus 0.44.6.2
- den unveränderten 0.44.4-Suchkern
- 7er-Arbeitspakete
- fünf Sekunden normale Browserpause
- echte Weiter-Navigation
- persistente Fortschrittssicherung
- genau einen automatischen Fehler-Resume nach 90 Sekunden

Die Recovery- und Lazy-Bootstrap-Experimente aus 0.44.6.3 und 0.44.6.4 bleiben deaktiviert.

## 0.44.6.6 – 120/90-Cooldown-Test

0.44.6.6 ist ausdrücklich eine Testversion und ersetzt 0.44.6.5 nicht als Referenz.

Einzige Verhaltensänderung:

```text
mindestens 120 eindeutige Treffer
→ aktuelles Paket vollständig speichern
→ vor dem nächsten Suchauftrag 90 Sekunden warten
→ automatisch weiterlaufen
```

Die Pause läuft im Browser als `client_request_gate`. Der Worker erhält währenddessen keinen Request. Die Pause wird pro Session nur einmal ausgelöst.

Unverändert:

- Worker-Einstieg
- Parser und Extraktion
- Pagination
- 7er-Paketgröße
- 5-Sekunden-Normalpause
- Ampel und Filter
- Retry-Verhalten
- 0.44.6.2-Fehler-Recovery
- Karten und UI

### Live-Abnahme

1. Bis mindestens 120 eindeutige Treffer muss der Lauf exakt der Referenz 0.44.6.5 entsprechen.
2. Nach der Schwelle müssen `cooldown_threshold_reached` und vor dem nächsten Request `cooldown_start` erscheinen.
3. Zwischen `cooldown_start` und `cooldown_resume` dürfen mindestens 90 Sekunden lang keine neuen `/api/search`-Ereignisse erscheinen.
4. Nach `cooldown_resume` muss die gleiche Session automatisch mit dem nächsten Arbeitspaket weiterlaufen.
5. Die Pause darf in derselben Session nicht erneut erscheinen.
6. Ergebnisse, Dubletten, Preise, Bilder, Ampeln und Datenkonsistenz müssen unverändert bleiben.
7. Der entscheidende Vergleichswert ist der Fehlerpunkt beziehungsweise die maximal erreichte Trefferzahl gegenüber 0.44.6.5.

Bei einer Regression wird direkt auf 0.44.6.5 zurückgeschaltet. Nur ein reproduzierbarer Vorteil rechtfertigt eine spätere Übernahme.

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
