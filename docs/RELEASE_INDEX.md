# GenericParser Release-Index

Dieser Index ordnet die produktiven Versionsstände ihren Build-IDs und Abschluss-Commits zu. Ein Abschluss-Commit bezeichnet den letzten technischen Commit des jeweiligen Release-Bündels; spätere reine Metadaten-Commits ändern diesen technischen Stand nicht.

| Version | Build-ID | Technischer Abschluss-Commit | Schwerpunkt |
|---|---|---|---|
| 0.42.3 | `gp-0423-20260802-1` | `9c8841fecac53ffaa127a7ed83ca94492a260a88` | Pagination-Stopp bei erreichter Gesamtzahl und kurzer HTML-Seite |
| 0.42.2 | `gp-0422-20260802-1` | `05c77b77d31a34c88dd2721f975492a6bac899fb` | App-freier Ein-Seiten-Service, Datenfluss- und Konsistenzprüfung |
| 0.42.1 | `gp-0421-20260802-1` | `6cdb40edcc3ef0faf2ba73a62086a68fc6452d85` | Zentraler UI-Zustand und aktivierter Suchbutton |
| 0.42.0 | `gp-0420-20260802-1` | `f6fe54a2878a13f357633f603199021890d05c75` | Lazy-Bootstrap und importstabiler Readiness-Pfad |
| 0.41.1 | `gp-0411-20260802-1` | `4c9eac9e52a34c52a021ff5d74c2d87ad0c5351d` | Deployment-Handshake und Build-Kopplung |
| 0.41.0 | – | `e3eb36a63b57d2d80fec820550d897718fde4249` | Ressourcendiagnose pro Seite |
| 0.40.9 | – | `77c8b51f1ee04a9fe0950a7c1189c2d383dc8a68` | Serverphasen und mobile Layoutkorrekturen |
| 0.40.8 | – | `d937eca2f755f115d567d988fe6bd40007cad748` | Erweiterte Request-/Antwortdiagnose |
| 0.40.7 | – | `8bc5e70ec1699e47011ffff2eda346d9380484e6` | Zentraler Session-Controller und Eventlog-Drosselung |
| 0.40.6 | – | `21d0f07c118f7066bcf464e8d705db7e1a94b453` | Sanfter Stopp und Eventlog-Unterseite |
| 0.40.5 | – | `d3fa989dd2f0445b3423011dbde857fd61608385` | Worker-Diagnosephasen |
| 0.40.4 | – | `f2c8da1f8710c4221f31ca8667f384ca3576b75e` | 1101-Hotfix und stabiler Page-Worker |
| 0.40.3 | – | `8b0135f03e6cf045fbb75d9b83345fdb87829ebe` | Integrierte Session-Steuerung |

## Aktueller Produktionsstand

```text
Version:      0.42.3
Paketversion: 0.42.3
Build-ID:     gp-0423-20260802-1
API-Vertrag:  match-v6.1-page-worker
Worker:       bootstrap+app-free-one-page-service
Code-Commit:  9c8841fecac53ffaa127a7ed83ca94492a260a88
```

## Downloadformat

Der technisch abgeschlossene Stand 0.42.3 kann direkt geladen werden:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/9c8841fecac53ffaa127a7ed83ca94492a260a88.zip
```

Der aktuelle Hauptbranch einschließlich nachgezogener Dokumentation ist unter folgendem Standardpfad verfügbar:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/refs/heads/main.zip
```

## Pflegevorgabe für neue Releases

Bei jedem neuen Versionsstand müssen gemeinsam aktualisiert werden:

1. `README.md`
2. `CHANGELOG.md`
3. `pyproject.toml`
4. dieser Release-Index
5. `VERSION.json`
6. UI-Version und Build-ID
7. Controller und Handshake
8. Worker-Version, Build-ID und API-Vertrag
9. Eventlog-Schlüssel und Eventlog-Anzeige
10. Service-Worker-Cache
11. statische Versions- und Datenflussprüfungen
