# GenericParser Release-Index

Dieser Index ordnet die Versionsstände ihren Build-IDs und technischen Abschlussständen zu. Reine Dokumentations-Commits nach dem technischen Abschluss ändern den Suchkern nicht.

| Version | Build-ID | Technische Basis | Schwerpunkt |
|---|---|---|---|
| 0.45.1 | `gp-0451-20260807-1` | 0.45.0 / `search_service_v0450` | CORS, Preflight, Health/Version/Diagnostics, Request-Tracing, Logging und Deployment-Abnahme; Suchlogik unverändert |
| 0.45.0 | `gp-0450-20260805-1` | `f3697768cfed4828b5e4470d6ad0780451718252` | Versionierter Modulvertrag v1, Legacy-Suche auf Referenz 0.44.6.5, Evercade-/SNES-Adapter, Debug-Logs und netzwerkfreie Selbsttests |
| 0.44.6.6.1 Test | `gp-044661-20260805-1` | `5eab770c209ec18ec70e5233ac87e96b72f9780d` | Recovery-/Cooldown-Experiment; verworfen |
| 0.44.6.6 Build 3 Test | `gp-04466-20260804-3` | `61dad4d64b52c33f71927bc3ba2cbeb7ced92b78` | Referenzsicherer Cooldown-Test |
| 0.44.6.5 | `gp-04465-20260804-1` | `ddba9bf55c999b349d98f1438b31a710bd570155` | Stabile Rückfallreferenz mit 0.44.4-Suchkern |
| 0.44.6.2 | `gp-04462-20260804-1` | `f55f31bcd878ec1edb0b8fc0ee9b5330c8ef0a0a` | Bestätigte Arbeitsreferenz; 34 Arbeitspakete und 219 Ergebnisse |
| 0.44.6 | `gp-0446-20260804-1` | `1178738c76fed1f5ff08b3f5841eb869650073ff` | Funktionaler Rückbau auf den 0.44.4-Suchkern |
| 0.44.4 | `gp-0444-20260803-1` | `315f19f1cb928f7c3005851d4b74c08770abe592` | Fachlicher Referenzkern und Ampel nur für aktive Regeln |
| 0.42.7 | `gp-0427-20260803-1` | `119a05985d11017940b775bb2c6cc7bc6acd992a` | Virtuelle Arbeitspakete, maximal sieben Karten, fünf Sekunden Pause |
| 0.41.1 | `gp-0411-20260802-1` | `4c9eac9e52a34c52a021ff5d74c2d87ad0c5351d` | Deployment-Handshake |

## Aktueller Stand

```text
Version:                    0.45.1
Paketversion:               0.45.1
Build-ID:                   gp-0451-20260807-1
Modulvertrag:               generic-parser-module-v1
Fachlicher Referenzkern:    0.44.4
Stabile Rückfallreferenz:   0.44.6.5
Laufzeitbasis:              0.44.6.2
Suchservice:                search_service_v0450 unverändert
CORS:                       global, OPTIONS unterstützt
Diagnose:                   /health, /version, /diagnostics
Status:                     Stable Candidate; Release- und Live-Abnahme durch CI/Deploy
```

## Downloadformat

Nach dem finalen Release-Commit wird das exakte Archiv über den Commit-SHA bereitgestellt:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/<FINAL_COMMIT>.zip
```

Stabile Referenz 0.44.6.5:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/ddba9bf55c999b349d98f1438b31a710bd570155.zip
```

Aktueller Hauptbranch einschließlich Dokumentation:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/refs/heads/main.zip
```

## Pflegevorgabe

Bei jedem folgenden Release sind gemeinsam zu aktualisieren: README, Changelog bzw. versionsgebundene Release Notes, Roadmap, Paketversion, Release-Index, `VERSION.json`, API-Dokumentation, Funktions- und Limitierungsbeschreibung, UI/Worker-Identität, Service-Worker-Cache, Regressionstests, GitHub-Metadaten sowie CI- und Cloudflare-Livenachweis.

Verbindlicher Ablauf: [`docs/RELEASE_PROCESS.md`](RELEASE_PROCESS.md). Vollständiger Snapshot für 0.45.1: [`docs/API_0.45.1.md`](API_0.45.1.md) und [`docs/releases/0.45.1.md`](releases/0.45.1.md).
