# Verbindlicher Release-Prozess

Dieser Prozess gilt ab 0.45.0 für alle folgenden GenericParser-Releases, einschließlich Test-, Release-Candidate- und Hotfix-Versionen.

## 1. Grundsatz

Code, API-Dokumentation, Funktionsbeschreibung, Plattformgrenzen, Metadaten und Prüfnachweise bilden ein gemeinsames Release. Eine Versionsnummer allein ist kein vollständiges Release.

Jeder Stand muss eindeutig beantworten:

- Welche Funktion ist enthalten?
- Welcher API-Vertrag gilt?
- Welche Projekte können ihn wie nutzen?
- Welche Grenzen und bekannten Fehler bestehen?
- Welcher Commit ist der technische Abschluss?
- Welche CI- und Live-Prüfungen wurden durchgeführt?
- Wie wird auf die letzte stabile Referenz zurückgefallen?

## 2. Versions- und Buildschema

- Produkt- und Paketversion folgen Semantic Versioning, beispielsweise `0.45.0`.
- Git-Tag: `v<VERSION>`, beispielsweise `v0.45.0`.
- Build-ID: `gp-<VERSION ohne Punkte>-<YYYYMMDD>-<laufende Nummer>`.
- Teststände erhalten einen eindeutigen Versions- oder Pre-Release-Zusatz und werden als `prerelease` markiert.
- Ein Build darf seine ID nach Veröffentlichung nicht wiederverwenden.

## 3. Pflichtdateien je Release

| Artefakt | Pflichtinhalt |
|---|---|
| `VERSION.json` | vollständige maschinenlesbare Metadaten, Referenzen und Prüfstatus |
| `docs/API_<VERSION>.md` | vollständiger versionsgebundener API-Snapshot einschließlich Projektintegration und Grenzen |
| `docs/releases/<VERSION>.md` | Release Notes, Commit-/Builddaten, Änderungen, bekannte Grenzen, Prüfmatrix, Rollback |
| `README.md` | aktueller Stand und Links auf die Release-Dokumente |
| `CHANGELOG.md` | fachliche und technische Änderungen |
| `ROADMAP.md` | Status und nächste Schritte |
| `docs/RELEASE_INDEX.md` | Version, Build, technischer Commit und Schwerpunkt |
| aktive Identitätsdateien | identische Version, Build-ID und Vertrag in Python und Browser |
| Service Worker | neuer Cache-Name und aktive Assetliste |
| Tests/CI | aktualisierte Identitäts-, Vertrags-, PWA- und Deploymentprüfung |

Die API-Dokumentation ist auch dann zu aktualisieren, wenn sich keine Schnittstelle geändert hat. In diesem Fall muss ausdrücklich stehen, dass der Vertrag unverändert blieb, und welche Implementierungs- oder Plattformgrenzen für den neuen Stand gelten.

## 4. Inhalt der API-Dokumentation

Jeder Snapshot enthält mindestens:

1. Version, Build, Vertrag und Referenzstände.
2. Verantwortungsgrenze zwischen GenericParser und aufrufendem Projekt.
3. Authentisierung und Sicherheitsmodell.
4. Alle öffentlichen Endpunkte mit Methode und Zweck.
5. Vollständige Requestfelder, Typen, Standardwerte und Validierung.
6. Vollständige Responsefelder und Invarianten.
7. Fehlerstatus und Retry-Verhalten.
8. Pagination, Deduplizierung und Clientzustand.
9. Exakte Matching-, Filter- und Ampelfunktion.
10. Beispiele für Evercade und SNES-PAL, sofern die Adapter enthalten sind.
11. Debug- und Testschalter einschließlich Standardzustand.
12. Aktuelle offizielle Cloudflare-Free-Grenzen und ihre konkrete Auswirkung.
13. Bekannte funktionale und betriebliche Limitierungen.
14. Kompatibilitäts- und Migrationshinweise.

Plattformzahlen werden vor jedem Release gegen die offiziellen Cloudflare-Dokumente geprüft und mit Datum sowie Quellenlink festgehalten.

## 5. Strukturierte Metadaten

`VERSION.json` enthält mindestens:

- Produkt-, Paket- und Buildversion,
- API- und Modulvertrag,
- Release-Datum und Kanal,
- Git-Tag und Release-Name,
- technischen Abschluss-Commit,
- Pfade zu API-Dokumentation, Release Notes und Deployment-Dokumentation,
- Funktions- und Referenzbeschreibung,
- Debug- und Teststandard,
- Cloudflare-Free-Grenzen mit Stichtag und offizieller Quelle,
- CI- und Cloudflare-Live-Prüfstatus,
- Rollbackplan,
- Metadatenschemaversion.

`python scripts/check_release_metadata.py` prüft diese Angaben gegen Quellcode, Browseridentität, Paketversion und Pflichtdokumente.

## 6. Lokale Prüfung

Mindestens ausführen:

```bash
python scripts/check_release_metadata.py
python scripts/run_release_tests.py
node --check cloudflare/public/build-identity-0450.js
node --check cloudflare/public/controller-0450.js
node --check cloudflare/public/module-debug-0450.js
node --check cloudflare/public/auto-resume-0450.js
node --check cloudflare/public/eventlog-0450.js
node tests/check_module_debug_v0450.js
```

Versionierte Dateinamen werden bei einem späteren Release auf dessen aktive Dateien umgestellt.

Die ungefilterte Sammlung enthält archivierte Versionsassertionen, die frühere Stände jeweils als aktiven Worker erwarten und sich gegenseitig ausschließen. Die aktuelle Release-Suite wird deshalb verbindlich in `VERSION.json.release_test_suite.paths` geführt. Archivtests bleiben als Nachweis und über ihre historischen manuellen Workflows erhalten.

## 7. GitHub-CI

Jeder Commit auf `main` erhält den allgemeinen Check `GenericParser release integrity`. Er darf keine Pfadfilter haben, damit auch reine Metadaten- oder Dokumentationscommits einen Status liefern.

Runtime-relevante Änderungen lösen zusätzlich den Cloudflare-Workflow aus. Dieser muss:

1. Release-Metadaten und Tests prüfen.
2. Secrets ausdrücklich validieren.
3. exakt den geprüften Commit deployen.
4. die veröffentlichte URL ermitteln.
5. Health, Version, Vertrag, Profilvalidierung und netzwerkfreien Selbsttest live prüfen.
6. ein begrenztes echtes Modul-Arbeitspaket ausführen.

Ein übersprungener Live-Schritt gilt nicht als bestandene Liveprüfung.

## 8. GitHub-Release-Metadaten

Für die Veröffentlichung werden gepflegt:

- Tag `v<VERSION>`,
- Release-Name aus `VERSION.json`,
- vollständige Beschreibung aus `docs/releases/<VERSION>.md`,
- Kennzeichnung `prerelease` passend zum Kanal,
- automatisch erzeugte Kategorien aus `.github/release.yml`,
- Quellcode-ZIP des Tags,
- Link auf die vollständige API-Dokumentation,
- Rollback- und Referenzlink.

Ein GitHub-Release zeigt auf den final geprüften Commit. Reine Nachweisdokumentation nach dem technischen Abschluss darf den technischen Commit getrennt ausweisen, muss aber im Release-Tag enthalten sein.

## 9. Abschluss und Prüfstatus

Die Release Notes enthalten eine Matrix:

| Prüfung | Status | Nachweis |
|---|---|---|
| lokale Tests | offen/bestanden/fehlgeschlagen | Befehl und Ergebnis |
| GitHub Release Integrity | offen/bestanden/fehlgeschlagen | Actions-Link |
| Cloudflare Deployment | offen/bestanden/fehlgeschlagen | Actions-Link |
| Live Health/Vertrag | offen/bestanden/fehlgeschlagen | URL, Zeitpunkt, Build |
| begrenzte Live-Suche | offen/bestanden/fehlgeschlagen | Query, Paket, Ergebnis oder Fehler |

Erst bei allen verpflichtenden Prüfungen auf `bestanden` wird `VERSION.json.status` auf einen bestätigten Release-Status gesetzt. Ist ein externer Zugang oder Dienst blockiert, wird der Release nicht als bestätigt bezeichnet; der Blocker wird konkret dokumentiert.

## 10. Rollback

- Die letzte bestätigte Referenz bleibt als Commit-ZIP und Git-Referenz verfügbar.
- Ein Rollback verändert nicht rückwirkend die Dokumentation des fehlerhaften Releases.
- Release Notes nennen Ursache, Zielcommit und betroffene Funktionen.
- Experimentelle Recovery- oder Parseränderungen werden nicht in die stabile Referenz übernommen, bevor ein realer Vergleichslauf bestanden ist.

## 11. Pull-Request-Checkliste

- [ ] Versions- und Buildidentität vollständig abgeglichen
- [ ] API-Snapshot für die Version angelegt oder aktualisiert
- [ ] Funktion und Limitierungen vollständig beschrieben
- [ ] Cloudflare-Grenzen offiziell geprüft und datiert
- [ ] Release Notes, Changelog, Roadmap und Index aktualisiert
- [ ] `VERSION.json` vollständig und valide
- [ ] Service-Worker-Cache rotiert
- [ ] lokale Prüfungen bestanden
- [ ] GitHub-CI bestanden
- [ ] Cloudflare-Liveprüfung bestanden oder Blocker dokumentiert
- [ ] Tag-/Release-Name, Rollback und Downloadverweise vorbereitet
