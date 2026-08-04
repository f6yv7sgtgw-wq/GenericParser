# GenericParser Release-Index

Dieser Index ordnet die Versionsstände ihren Build-IDs und technischen Abschluss-Commits zu. Reine Dokumentations-Commits nach dem technischen Abschluss ändern den Code-Stand nicht.

| Version | Build-ID | Technischer Abschluss-Commit | Schwerpunkt |
|---|---|---|---|
| 0.44.6.3 | `gp-04463-20260804-1` | `681f4365937360419d4eb22042180bff981a46ff` | Recovery-Probe, gestaffeltes Backoff mit Jitter, bis zu zwei automatische Fortsetzungen; Live-Test ausstehend |
| 0.44.6.2 | `gp-04462-20260804-1` | `f55f31bcd878ec1edb0b8fc0ee9b5330c8ef0a0a` | Einmalige automatische Fortsetzung; bestätigte Arbeitsreferenz mit 219 Ergebnissen vor Recovery |
| 0.44.6.1 | `gp-04461-20260804-1` | `8f5b76cdcfe469f8ae4005a9dd5ee23d6d451931` | Diagnosefix und verständliche 503-/Referenzanzeige |
| 0.44.6 | `gp-0446-20260804-1` | `1178738c76fed1f5ff08b3f5841eb869650073ff` | Funktionaler Rückbau auf den 0.44.4-Suchkern |
| 0.44.5.2 | `gp-04452-20260804-1` | `6a77260ba8d5db781f0ce9f58b770fa53520d672` | Experimentelle Direct-Worker-Linie; nicht als Referenz verwendet |
| 0.44.5.1 | `gp-04451-20260804-1` | `41f5510f4408435cae9b3e8f36bfa5a8a6a28c2d` | Extraktionshotfix der experimentellen Runtime |
| 0.44.5 | `gp-0445-20260804-1` | `4a43f34bed8ec9dba9bb830965c4ce29dfdfe739` | Direkter Free-Worker-Versuch |
| 0.44.4 | `gp-0444-20260803-1` | `315f19f1cb928f7c3005851d4b74c08770abe592` | Fachlicher Referenzkern und Ampel nur für aktive Regeln |
| 0.42.7 | `gp-0427-20260803-1` | `119a05985d11017940b775bb2c6cc7bc6acd992a` | Virtuelle Arbeitspakete, maximal sieben Karten, fünf Sekunden Pause |
| 0.42.6 | `gp-0426-20260802-1` | `9607acd28752e571d322cada01c66c20c5f1035f` | Readiness-Bootstrap und Diagnosebasis |
| 0.42.5 | `gp-0425-20260802-1` | `81bcedec1bf485faf49264c57af418a958fa8531` | Experimenteller FFI-Transport; verworfen |
| 0.42.4 | `gp-0424-20260802-1` | `e54d33649371f7c2ca9099fd7d2712c2744b7817` | Gemeinsame Build-Identität einschließlich Eventlog |
| 0.42.3 | `gp-0423-20260802-1` | `9c8841fecac53ffaa127a7ed83ca94492a260a88` | Pagination-Stopp bei Gesamtzahl und kurzer HTML-Seite |
| 0.42.2 | `gp-0422-20260802-1` | `05c77b77d31a34c88dd2721f975492a6bac899fb` | App-freier Ein-Seiten-Service und Konsistenzprüfung |
| 0.42.1 | `gp-0421-20260802-1` | `6cdb40edcc3ef0faf2ba73a62086a68fc6452d85` | Zentraler UI-Zustand |
| 0.42.0 | `gp-0420-20260802-1` | `f6fe54a2878a13f357633f603199021890d05c75` | Lazy-Bootstrap |
| 0.41.1 | `gp-0411-20260802-1` | `4c9eac9e52a34c52a021ff5d74c2d87ad0c5351d` | Deployment-Handshake |

## Aktueller Stand

```text
Version:               0.44.6.3
Paketversion:          0.44.6.3
Build-ID:              gp-04463-20260804-1
API-Vertrag:           match-v6.11.4-reference-recovery-hardening
Fachlicher Referenzkern: 0.44.4
Arbeitsreferenz:       0.44.6.2
Status:                Implementiert, Cloudflare-Live-Test ausstehend
```

## Downloadformat

Technischer Abschlussstand 0.44.6.3:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/681f4365937360419d4eb22042180bff981a46ff.zip
```

Aktueller Hauptbranch einschließlich Dokumentation:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/refs/heads/main.zip
```

## Pflegevorgabe

Bei neuen Releases gemeinsam aktualisieren: README, Changelog, Paketversion, Release-Index, `VERSION.json`, UI, Controller, Worker, Eventlog, Cache-Busting und Regressionstests.
