# GenericParser 0.44.6.3 Build 2 – Resume-Control-Hotfix

## Live-Befund aus Build 1

Der Suchlauf speicherte 113 Ergebnisse und endete nach einer HTML-503-/Cloudflare-1101-Kette mit `retry_exhausted`. Die neue `/api/recovery-probe` war anschließend erfolgreich. Trotzdem startete die automatische Fortsetzung nicht und auch der manuelle Klick auf **Letzte Suche fortsetzen** blieb ohne Wirkung.

Das Eventlog zeigte:

```text
recovery_probe_ready
→ resume_control_unavailable
→ manual_required
```

## Ursache

Der Referenzcontroller ließ die Fortsetzen-Schaltfläche nach einem terminalen Fehler sichtbar, aber weiterhin mit `disabled=true`. Der Recovery-Controller wartete deshalb vergeblich auf einen sichtbaren **und** aktivierten Button. Ein Programmatic Click auf einen deaktivierten Button wird ebenfalls nicht ausgeführt.

## Hotfix in Build 2

Build-ID: `gp-04463-20260804-2`

Der Controller synchronisiert die Schaltfläche alle 500 ms mit dem persistenten Recovery-Zustand.

Aktiviert wird sie in:

- `waiting`
- `probing`
- `starting_auto`
- `manual_required`

Während `running`, `auto_running`, `completed`, `cancelled` oder `cleared` wird sie wieder gesperrt beziehungsweise ausgeblendet.

Dadurch funktionieren:

- manuelles Fortsetzen während der Recovery-Wartezeit,
- manueller Fallback nach fehlgeschlagener Recovery,
- automatisches `button.click()` nach erfolgreicher Probe,
- Wiederherstellung nach einem Seiten-Reload.

Das Eventlog protokolliert die Freigabe mit `resume_control_ready`.

## Unverändert

- Suchkern `search_service_v0444`
- Pagination
- Extraktion
- Ampellogik
- Paketgröße 7
- normale Pause 5 Sekunden
- Backoff und Recovery-Probe aus 0.44.6.3 Build 1

## Abnahme

1. Vorhandenen Recovery-Zustand laden.
2. Prüfen, dass **Letzte Suche fortsetzen** sichtbar und aktiv ist.
3. Manuell fortsetzen und kontrollieren, dass eine neue `search_resume`-Session startet.
4. Bei der nächsten automatischen Recovery müssen `resume_control_ready`, `recovery_resume_start` und `recovery_resume_running` erscheinen.
5. Die Suche muss auf der gespeicherten Seite fortsetzen.
