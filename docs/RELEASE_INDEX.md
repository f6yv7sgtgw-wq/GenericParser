# GenericParser Release-Index

Dieser Index ordnet die maßgeblichen Versionsstände ihren Build-IDs und Abschluss-Commits zu. Historische Zwischenstände bleiben über Git-Historie und `CHANGELOG.md` nachvollziehbar.

| Version | Build-ID | Abschluss-Commit | Schwerpunkt |
|---|---|---|---|
| 1.6.4 RC | `gp-164-20260812-1` | ausstehend | Reiner Versionsbump ohne funktionale Änderung; verifiziert Build, Deployment und Auslieferung einer neuen Version bis auf das Endgerät |
| 1.6.3 RC | `gp-163-20260810-1` | ausstehend | Mobiles `Load failed` in langen API-v2-Läufen automatisch wiederholen; Vinted-Hintergrunddetails geben der Hauptsuche Vorrang; gleicher Seitenstand behält flüchtige eBay-Treffer; eindeutige Quellen- und klare Detailzähler |
| 1.6.2 | `gp-162-20260810-1` | `9e2a09b71c6d6cea7bca4e13b0ecd2a515758907` | Safari-Startpfad fail-open; dynamische Endpunkte vom Asset-Cache getrennt; Log & Diagnose im aktuellen responsiven Farbschema; Produktions- und direkter Browser-v2-Test grün; Suchkern unverändert |
| 1.6.1 | `gp-161-20260810-1` | `0b30f5bf651a3b7a87401ace0dce0540d5b1c882` | Browser-Controller reicht API-v2-State korrekt weiter; Speicherräumung fail-open; freundlicheres tiefblaues/teal Farbschema; Produktions-Live-Gates grün; Modul-v1, v2-Schema und Suchkern unverändert |
| 1.6.0 | `gp-160-20260810-1` | `9a3f5af1775fbf1c95438dbb66daa643908235f3` | Modul-API v2 und neue Websuche; vor Stable-Freigabe wegen inkompatibler Controller-Aufrufsignatur durch 1.6.1 ersetzt |
| 1.5.1 | `gp-151-20260810-1` | `20721cc6335c00b6e1f9560c228f5604376f81b3` | Manueller Stopp eindeutig pausiert/fortsetzbar; ausgewogenes responsives Filterlayout; 1.5.0-Suchverhalten unverändert; Produktions-Live-Gates grün |
| 1.5.0 | `gp-150-20260810-1` | `33931e0dd391c68539ec1965342eff8a40d77070` | Produktklassifizierung, feste Ampelreihenfolge, Ergebnisfilter, kompakte Karten, explizite Browser-Favoriten und signierter eBay-Löschendpunkt; Produktions-Live-Gates grün |
| 1.4.0 | `gp-140-20260809-1` | `7eb1b9c6a124ee43f36555cfca7bce39ddd1e47c` | Offizielle eBay Browse API auf `EBAY_DE`, Festpreisstandard, bekannte Versand-Gesamtsumme und flüchtige eBay-Treffer; Produktions-Live-Gates grün |
| 1.3.4 | `gp-134-20260809-1` | `47a74efa13f63b0908688cc96872e013f23e56bf` | Dichtes Mehrspaltenraster, kleine Karten mit Bild und Text nebeneinander, Startseiten-Symbol entfernt; Produktions-Live-Gates grün |
| 1.3.3 | `gp-133-20260809-1` | `88df0a4f91fd813a685e26b429e3c549bb9ce5b3` | GUI-Rework im Evercade/SNES-Stil, Log-Navigation im Kopf und kompakte aufklappbare Vinted-Beschreibungen; Produktions-Live-Gates grün |
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

## Aktueller Release-Kandidat

```text
Version:                    1.6.4
Paketversion:               1.6.4
Build-ID:                   gp-164-20260812-1
Bevorzugter Modulvertrag:   generic-parser-module-v2
Kompatibler Modulvertrag:   generic-parser-module-v1
Worker-Profil:              Paid
Fachlicher Referenzkern:    0.44.4
Operative Referenz:         0.44.6.5
Suchruntime:                0.45.0
Neue-Suche-Cooldown:        0 ms
Normale Paketpause:         0 ms
Erfolgreiche Paketpause:    0 ms
Transport-Recovery:         250/750/1500/3000/5000/8000 ms, nur nach Fehler
Vinted Inline-Details:      maximal 3 je Katalogrequest
Vinted Hintergrund-Batch:  maximal 3, seriell je Client
Hauptsuche blockiert:       nein; Vinted-Hintergrunddetails warten auf ihr Ende
eBay-Transport:             offizielle Production Browse API
eBay-Marktplatz:            EBAY_DE
eBay-Festpreis:             standardmäßig an
eBay-Auktionen:             standardmäßig aus, explizit aktivierbar
eBay-Gesamtpreis:           Artikel + bekannte Versandkosten
Unbekannte Versandkosten:   price/total_price bleiben leer
eBay-Suchergebnispersistenz: keine
Explizite Favoriten:        browserlokal, ohne Verkäufer-/Kontodaten
eBay-Löschendpunkt:         ECDSA-signiert, Challenge unterstützt
Produktklassifizierung:     v1, erklärbar und quellenneutral
Ampelreihenfolge:           Grün, Gelb, Orange, Rot
Ergebnisfilter:             12 Filter-/Sortiergruppen plus aktive Chips
Term-Eingabe:               entfernbare Chips per Komma/Enter/Einfügen
Quellenfortschritt:         Kleinanzeigen, Vinted und eBay getrennt
Fortsetzung:                signiertes opakes Token, 2 Stunden
Serverseitige Suchjobs:     nein
Anzeigentext:               entfernt
Log-Navigation:             im Seitenkopf
Browser-Start:              eingebettete Identität, Live-Prüfung im Hintergrund
Diagnosefehler sperrt Suche: nein
Log-Oberfläche:             responsiv, API v2 klar von v1-Kompatibilität getrennt
Ergebnisraster:             3+ Spalten Desktop, 4–5 Spalten Wide Screen
Kartenmedien:               Bild und Text dauerhaft nebeneinander
Startseiten-Symbol:         entfernt
Debug-Logs:                 standardmäßig aus
Modultests:                 standardmäßig aus, ohne Kleinanzeigen-Abruf
Status:                     Release Candidate; Produktionsabnahme ausstehend
Produktions-Commit:         ausstehend
Deploy-Workflow:            ausstehend
Mobiler Paketfehler-Test:   30 Pakete; Paket 29 einmal verloren; 819 Treffer erhalten
Direkter Browser-v2-Test:   ausstehend
Live-Assets:                ausstehend
```

## Rückfallreferenz

```text
Version:                    1.6.2
Build-ID:                   gp-162-20260810-1
Commit:                     9e2a09b71c6d6cea7bca4e13b0ecd2a515758907
Deploy-Workflow:            31423346170 (success)
```

## Release-Download

Der Hauptbranch enthält den veröffentlichten Stand einschließlich der nachgelagerten Abnahme- und Release-Metadaten:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/refs/heads/main.zip
```

Der exakte abgenommene 1.6.2-Produktionsstand ist dauerhaft über den Commit abrufbar:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/9e2a09b71c6d6cea7bca4e13b0ecd2a515758907.zip
```

Stabile Rückfallreferenz 1.6.2:

```text
https://github.com/f6yv7sgtgw-wq/GenericParser/archive/9e2a09b71c6d6cea7bca4e13b0ecd2a515758907.zip
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
