# GenericParser 0.42.5

## Anlass

Cloudflare 0.42.4 verarbeitete den ersten Seitenrequest erfolgreich, während nachfolgende HTML-Fallback-Requests wiederholt mit Cloudflare-503 und schließlich 1101 vor ASGI endeten. Zusätzlich erzeugte die Eventlog-Versionsprüfung in Safari den Fehler `The string did not match the expected pattern`.

## Dokumentationsprüfung

- Der Einstieg `WorkerEntrypoint.fetch -> asgi.fetch(app, request, env)` entspricht dem offiziellen Cloudflare-FastAPI-Muster und bleibt unverändert.
- Python Workers laufen in Pyodide innerhalb eines V8-Isolates und können Workers-Runtime-APIs über die Python-JavaScript-FFI verwenden.
- 1101 bezeichnet eine unbehandelte Worker-Runtime-Ausnahme; maßgeblich sind Worker-Logs und Ray-ID.
- Cloudflare-generierte Fehler lassen sich zusätzlich über `cf-error-type`, `cf-error-origin` und `cf-ray` unterscheiden.
- Worker-Subrequests unterliegen Runtime-Limits; unnötige bzw. nicht sauber abgeschlossene Netzwerkpfade sind zu vermeiden.

## Änderungen

- Ausgehende Kleinanzeigen-Requests verwenden in Produktion den nativen Workers-`fetch()` über die Python-JavaScript-FFI.
- `httpx` bleibt nur als lokaler Test-Fallback bestehen.
- HTML- und Mobile-API-Antworten erfassen `cf-error-type` und `cf-ray`.
- ASGI-Einstieg und FastAPI-Routing bleiben unverändert.
- Eventlog und Deployment-Handshake bauen `/api/version` mit einer absoluten URL auf Basis von `window.location.href`.
- Content-Type des Versionsendpunkts wird vor dem JSON-Parsing geprüft.
- Pagination-Guard aus 0.42.3 bleibt aktiv.

## Gemeinsame Identität

- Version: `0.42.5`
- Build-ID: `gp-0425-20260802-1`
- API-Vertrag: `match-v6.1-page-worker`
- Transport: `workers-fetch-ffi`

## Prüfung

Die Versionspfade, der produktive Python-Einstieg, Worker-Bootstrap, Search-Service, UI, Controller, Handshake, Eventlog und PWA-Cache wurden statisch auf 0.42.5 abgeglichen. Ein echter Cloudflare-Live-Test muss nach dem Deployment erfolgen.
