# GenericParser Release-Index

Dieser Index ordnet die maßgeblichen Versionsstände ihren Build-IDs und Abschluss-Commits zu. Historische Zwischenstände bleiben über Git-Historie und `CHANGELOG.md` nachvollziehbar.

| Version | Build-ID | Abschluss-Commit | Schwerpunkt |
|---|---|---|---|
| 1.3.3 | `gp-133-20260809-1` | ausstehend | GUI-Rework im Evercade/SNES-Stil, Log-Navigation im Kopf und kompakte aufklappbare Vinted-Beschreibungen |
| 1.3.2 | `gp-132-20260809-1` | `cece9c4723eca97fb38627493628468b21e5fb86` | Entkoppelte Vinted-Hintergrundanreicherung in seriellen 3er-Batches, Live-Updates und erneutes Scoring; Produktions-Live-Gates grün |
| 1.3.1 | `gp-131-20260809-1` | `506bdd234304e215ca77ae58f217f6217c5a206c` | Timeout-sichere Vinted-Detailanreicherung: höchstens drei Detailseiten je Katalogrequest |
| 1.3.0 | `gp-130-20260808-1` | `070fc93276bccf9d3a7b77e5e94da86d6669e3e3` | Erste Vinted-Detailanreicherung; wegen etwa 49 Sekunden blockierendem Live-Request durch 1.3.1 ersetzt |
| 1.2.2 Build 4 | `gp-122-20260808-4` | `b1a6603bb6a1888c6de5fca30e1453430fc8e5d5` | Runtime-geladene öffentliche Identität und produktives Vinted Service Binding |
| 1.0.0 | `gp-100-20260808-1` | `e475638d4a9f2544ab4cd9efe7581471e8fec07f` | Erster Stable Release; Paid Worker; keine künstlichen Free-Worker-Wartezeiten; Modulvertrag v1; Evercade/SNES kompatibel |
| 0.45.2 Build 7 Paid | `gp-0452-20260808-7` | `70c22ee4cda2f029490fb6825668db57358e4aa5` | Letzter bestätigter Pre-1.0-Produktionsstand; Schutz- und Wartezeiten deaktiviert |
| 0.45.0 | `gp-0450-20260805-1` | `f3697768cfed4828b5e4470d6ad0780451718252` | `generic-parser-module-v1`, Evercade-/SNES-Adapter, modulare API |
| 0.44.6.5 | `gp-04465-20260804-1` | `ddba9bf55c999b349d98f1438b31a710bd570155` | Operative Rückfallreferenz |
| 0.44.4 | `gp-0444-20260803-1` | `315f19f1cb928f7c3005851d4b74c08770abe592` | Fachlicher Suchkern und Ampellogik |
| 0.42.7 | `gp-0427-20260803-1` | `119a05985d11017940b775bb2c6cc7bc6acd992a` | 7er-Arbeitspakete für Cloudflare Worker |
| 0.41.1 | `gp-0411-20260802-1` | `4c9eac9e52a34c52a021ff5d74c2d87ad0c5351d` | Deployment-Handshake |

## Aktueller Release Candidate

```text
Version:                    1.3.3
Paketversion:               1.3.3
Build-ID:                   gp-133-20260809-1
Modulvertrag:               generic-parser-module-v1
Worker-Profil:              Paid
Fachlicher Referenzkern:    0.44.4
Operative Referenz:         0.44.6.5
Suchruntime:                0.45.0
Neue-Suche-Cooldown:        0 ms
Normale Paketpause:         0 ms
Retry-Wartezeiten:          0 ms
Vinted Inline-Details:      maximal 3 je Katalogrequest
Vinted Hintergrund-Batch:  maximal 3, seriell je Client
Hauptsuche blockiert:       nein
Vinted-Beschreibung:        4 Zeilen, aufklappbar
Hashtag-Blöcke:             ausgeblendet
Log-Navigation:             im Seitenkopf
Debug-Logs:                 standardmäßig aus
Modultests:                 standardmäßig aus, ohne Kleinanzeigen-Abruf
Status:                     Release candidate; Produktions-Live-Gates ausstehend
Produktions-Commit:         ausstehend
Deploy-Workflow:            ausstehend
Vinted-Browser-Workflow:    ausstehend
```

## Release-Download

Nach der Produktionsabnahme wird der 1.3.3-Abschluss-Commit hier festgehalten. Der aktuelle Hauptbranch bleibt über folgenden Download erreichbar:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/refs/heads/main.zip
```

Stabile Rückfallreferenz 1.3.2:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/cece9c4723eca97fb38627493628468b21e5fb86.zip
```

## Pflegevorgabe ab 1.0

Bei jedem Stable Release gemeinsam aktualisieren:

- `README.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- `VERSION.json`
- `pyproject.toml`
- `docs/RELEASE_INDEX.md`
- Release-Dokumentation unter `docs/releases/`
- UI-/Worker-Build-Identität
- Cache-Busting
- Regressionstests
- Produktions-Deploy-Workflow
- Live-Verifikation und exaktes ZIP
