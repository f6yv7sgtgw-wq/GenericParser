# Repository-Regeln für Releases

Diese Regeln gelten ab GenericParser 0.45.0 für jede produktive Version und jede Testversion.

## Verbindliche Release-Artefakte

Bei jedem Release sind gemeinsam zu aktualisieren:

- Produkt-, Paket-, Build- und Vertragsversionen,
- `VERSION.json` einschließlich Release-, Dokumentations-, Plattform- und Prüfmetadaten,
- `CHANGELOG.md`, `README.md`, `ROADMAP.md` und `docs/RELEASE_INDEX.md`,
- versionsgebundene vollständige API-Dokumentation `docs/API_<VERSION>.md`,
- versionsgebundene Release Notes `docs/releases/<VERSION>.md`,
- Funktionsbeschreibung einschließlich bekannter Grenzen und aktueller Cloudflare-Free-Limits,
- aktive UI-, Worker-, Controller-, Eventlog- und Service-Worker-Identität,
- Regressionstests und GitHub-CI,
- Cloudflare-Liveprüfung oder ein ausdrücklich dokumentierter Blocker,
- Download-, technischer Commit- und Rollbackverweis.

Ein Release darf nicht als vollständig abgenommen bezeichnet werden, solange der erforderliche CI- oder Live-Nachweis offen ist.

## Referenzschutz

- Der fachliche Suchkern 0.44.4 und die operative Rückfallreferenz 0.44.6.5 bleiben unverändert, solange eine Änderung nicht ausdrücklich als neuer fachlicher Umfang beschlossen wurde.
- Release-, Dokumentations-, CI- oder Diagnosearbeiten dürfen den Suchfluss nicht beiläufig ändern.
- Debug-Logs und Selbsttests bleiben standardmäßig deaktiviert.
- Selbsttests bleiben ohne Kleinanzeigen-Abruf, sofern ein Release nicht ausdrücklich einen getrennten Live-Test benennt.

## Pflichtprüfung

Vor Veröffentlichung ausführen:

```bash
python scripts/check_release_metadata.py
python scripts/run_release_tests.py
node tests/check_module_debug_v0450.js
```

Die vollständige ungefilterte Testsammlung enthält historische Assertions, die jeweils eine frühere Version als aktiven Produktionsstand verlangen. Für den aktuellen Release ist deshalb ausschließlich die in `VERSION.json.release_test_suite` ausgewiesene Suite maßgeblich; historische Workflows bleiben manuell ausführbar.

Der vollständige Ablauf und die GitHub-Metadaten stehen in `docs/RELEASE_PROCESS.md`.
