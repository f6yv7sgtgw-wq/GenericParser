# GenericParser Release-Index

| Version | Build-ID | Technische Basis | Schwerpunkt |
|---|---|---|---|
| 0.45.2 | `gp-0452-20260807-1` | 0.45.1 Edge/ASGI + unverändertes `search_service_v0450` | Dependency-freie Health/Version/Diagnostics/OPTIONS-Schicht, Lazy-ASGI, CORS-Fehlerfallback und echter Browser-CORS-Live-Gate |
| 0.45.1 | `gp-0451-20260807-1` | 0.45.0 / `search_service_v0450` | CORS, Preflight, Health/Version/Diagnostics, Request-Tracing, Logging und Deployment-Abnahme; Suchlogik unverändert |
| 0.45.0 | `gp-0450-20260805-1` | `f3697768cfed4828b5e4470d6ad0780451718252` | Versionierter Modulvertrag v1, Evercade-/SNES-Adapter, Debug und Selbsttests |
| 0.44.6.5 | `gp-04465-20260804-1` | `ddba9bf55c999b349d98f1438b31a710bd570155` | Tiefe stabile Rückfallreferenz mit 0.44.4-Suchkern |
| 0.44.4 | `gp-0444-20260803-1` | `315f19f1cb928f7c3005851d4b74c08770abe592` | Fachlicher Suchkern |

## Aktueller Stand

```text
Version:                  0.45.2
Paketversion:             0.45.2
Build-ID:                 gp-0452-20260807-1
Modulvertrag:             generic-parser-module-v1
Technische Basis:         0.45.1
Suchservice:              search_service_v0450 unverändert
Fachlicher Referenzkern:  0.44.4
Tiefe Rückfallreferenz:   0.44.6.5
Edge-Diagnose:            dependency-frei
Preflight:                dependency-frei
Status:                   Stable Candidate bis erfolgreicher Cloudflare-Live-Gate
```

## Download

Das finale 0.45.2-Archiv wird nach dem Squash-Merge über den exakten Main-Commit bereitgestellt:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/<FINAL_COMMIT>.zip
```

Rollback 0.45.1:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/994237ea196f6d8d84a12065eaa50f484295b089.zip
```

Vollständige Dokumentation: [`API_0.45.2.md`](API_0.45.2.md) und [`releases/0.45.2.md`](releases/0.45.2.md).
