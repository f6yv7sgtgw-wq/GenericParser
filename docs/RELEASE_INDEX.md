# GenericParser Release-Index

Dieser Index ordnet die maßgeblichen Versionsstände ihren Build-IDs und Abschluss-Commits zu. Historische Zwischenstände bleiben über Git-Historie und `CHANGELOG.md` nachvollziehbar.

| Version | Build-ID | Abschluss-Commit | Schwerpunkt |
|---|---|---|---|
| 1.0.0 | `gp-100-20260808-1` | wird beim Merge von PR gesetzt | Erster Stable Release; Paid Worker; keine künstlichen Free-Worker-Wartezeiten; Modulvertrag v1; Evercade/SNES kompatibel |
| 0.45.2 Build 7 Paid | `gp-0452-20260808-7` | `70c22ee4cda2f029490fb6825668db57358e4aa5` | Letzter bestätigter Pre-1.0-Produktionsstand; Schutz- und Wartezeiten deaktiviert |
| 0.45.0 | `gp-0450-20260805-1` | `f3697768cfed4828b5e4470d6ad0780451718252` | `generic-parser-module-v1`, Evercade-/SNES-Adapter, modulare API |
| 0.44.6.5 | `gp-04465-20260804-1` | `ddba9bf55c999b349d98f1438b31a710bd570155` | Operative Rückfallreferenz |
| 0.44.4 | `gp-0444-20260803-1` | `315f19f1cb928f7c3005851d4b74c08770abe592` | Fachlicher Suchkern und Ampellogik |
| 0.42.7 | `gp-0427-20260803-1` | `119a05985d11017940b775bb2c6cc7bc6acd992a` | 7er-Arbeitspakete für Cloudflare Worker |
| 0.41.1 | `gp-0411-20260802-1` | `4c9eac9e52a34c52a021ff5d74c2d87ad0c5351d` | Deployment-Handshake |

## Aktueller Stable-Stand

```text
Version:                    1.0.0
Paketversion:               1.0.0
Build-ID:                   gp-100-20260808-1
Modulvertrag:               generic-parser-module-v1
Worker-Profil:              Paid
Fachlicher Referenzkern:    0.44.4
Operative Referenz:         0.44.6.5
Suchruntime:                0.45.0
Neue-Suche-Cooldown:        0 ms
Normale Paketpause:         0 ms
Retry-Wartezeiten:          0 ms
Debug-Logs:                 standardmäßig aus
Modultests:                 standardmäßig aus, ohne Kleinanzeigen-Abruf
Status:                     Stable nach grüner CI- und Live-Abnahme
```

## Release-Download

Nach dem Stable-Merge ist der exakte Release-Stand über den Merge-Commit als ZIP reproduzierbar. Zusätzlich erzeugt der 1.0.0-Live-Verifikationslauf ein exaktes Source-ZIP-Artefakt.

Aktueller Hauptbranch:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/refs/heads/main.zip
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
