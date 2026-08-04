# GenericParser 0.44.6.5 – sauberer Rollback

## Anlass

Der Live-Test von 0.44.6.4 scheiterte bereits beim ersten Suchauftrag mit HTML-503 beziehungsweise Cloudflare 1101. Es wurden 0 Seiten und 0 Ergebnisse verarbeitet. Damit war 0.44.6.4 gegenüber der bestätigten Arbeitsreferenz 0.44.6.2 eine Regression.

## Rollback-Quelle

- Version: `0.44.6.2`
- Referenzcommit: `f55f31bcd878ec1edb0b8fc0ee9b5330c8ef0a0a`
- bestätigter Teststand: 34 Arbeitspakete und 219 gespeicherte Ergebnisse vor einer späteren Unterbrechung

## Aktiver Pfad in 0.44.6.5

- Worker-Einstieg wie 0.44.6.2
- FastAPI-/ASGI-Bootstrap wie 0.44.6.2
- Suchservice delegiert unverändert an `search_service_v0444`
- Controller basiert auf `controller-0411.js` wie 0.44.6.2
- Recovery verwendet den unveränderten Code aus `auto-resume-04462.js`
- neuer, isolierter Recovery-Speicherschlüssel `generic-parser-auto-resume-04465`

## Deaktiviert

- vollständige Recovery-Probe aus 0.44.6.3
- gestaffelte zwei Auto-Resume-Zyklen aus 0.44.6.3
- direkter leichter Probe-Endpunkt aus 0.44.6.4
- Lazy-ASGI-Bootstrap aus 0.44.6.4

## Unverändert

- Suchkern 0.44.4
- Paketgröße 7
- Pause 5 Sekunden
- echte Weiter-Navigation
- Extraktion von Titel, Preis und Bild
- Deduplizierung
- aktive Ampelregeln
- Suchstandssicherung

## Abnahme

Eine neue Suche muss wieder mindestens das erste Arbeitspaket erfolgreich verarbeiten. Der lange Vergleichstest soll dieselbe Suchabdeckung wie 0.44.6.2 erreichen. Bis zur Cloudflare-Abnahme bleibt 0.44.6.2 die bestätigte operative Referenz.
