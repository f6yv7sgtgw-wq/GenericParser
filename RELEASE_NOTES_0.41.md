# GenericParser 0.41

## Ziel

0.41 ergänzt eine leichte Ressourcendiagnose pro Ergebnisseite, ohne den stabilen Ein-Seiten-Worker und den zentralen Browsercontroller erneut umzubauen.

## Messwerte

- gesamte Worker-Wandzeit pro Anfrage
- Python-Prozesszeit pro Anfrage
- HTML-URL-Aufbau
- HTML-Downloadzeit
- HTML-Parsezeit
- Zeit zur Ermittlung der gemeldeten Gesamtzahl
- gesamte HTML-Fallback-Zeit
- HTML-Antwortgröße
- Mobile-API-Gesamtzeit und Antwortgröße
- Anzahl geparster Karten

Cloudflare stellt dem Python-Worker keinen verlässlichen Live-Heap-Zähler und keine GC-Zählung bereit. Diese Werte werden deshalb als nicht verfügbar ausgewiesen und nicht geschätzt.

## Oberfläche und Eventlog

Die aktuellen Messwerte erscheinen in einer eigenen Ressourcenkarte. Zusätzlich werden sie als `resource_metrics` im bestehenden Eventlog gespeichert. Fehlerantworten enthalten – sofern ASGI erreicht wird – Phase, Ray-ID, Ziel-URL und die bis dahin erfassten Ressourcenwerte.

## Technischer Stand

- Worker: `cloudflare_v041`
- sichtbare Version: `0.41.0`
- PWA-Cache: `generic-parser-mobile-0.41.0`
- API-Diagnose: `/api/resource-status`
