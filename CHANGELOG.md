# Changelog

Die Einträge fassen die produktiven Entwicklungsstände zusammen. Einzelne Versionen bestehen aus mehreren technischen Commits; der Abschluss-Commit steht in `docs/RELEASE_INDEX.md`.

## 1.6.1 – 2026-08-10 – Browser-Bridge-Hotfix und freundlicheres Farbschema

- Den in der produktiven 1.6.0-Weboberfläche reproduzierten Signaturfehler behoben: Der dynamische Controller reicht den vollständigen API-v2-Suchzustand mit Batch-ID und Fortsetzungstoken wieder durch alle Wrapper und Retries.
- Fortsetzungsfehler 409/410 als nicht wiederholbare Clientfehler behandelt.
- Browserseitiges Löschen eines Suchstands fail-open ausgeführt, damit eine nicht verfügbare IndexedDB keinen erfolgreich abgeschlossenen Suchlauf in einen Fehler verwandelt.
- Eigenen JavaScript-Regressionsvertrag für Controller-v2-State-Forwarding, Batch-/Tokenbindung, Speicherräumung und Cache-Busting ergänzt.
- Dunkles Farbschema freundlicher gestaltet: tiefblaue Flächen, türkise Primäraktionen, warme Lavendelakzente und weichere Karten bei unverändertem responsivem Layout.
- Modul-v1, API-v2-Schema, Marketplace-Adapter, Suchkern, Klassifizierung, Favoriten und Stopp/Fortsetzen unverändert beibehalten.
- Produktionsabnahme erfolgreich: Workflow `31419552008` bestätigte auf Commit `0b30f5bf651a3b7a87401ace0dce0540d5b1c882` Identität, Modul-v2, alle drei Marketplace-Quellen, eBay-Verträge und Vinted-Detailanreicherung; ein zusätzlicher direkter Browser-v2-Lauf bestätigte Batch-/Fortsetzungstoken über Kleinanzeigen, Vinted und eBay sowie bytegleiche Live-Assets.
- 1.6.0 vor Stable-Freigabe ersetzt; Rollback-Ziel bleibt 1.5.1 / `gp-151-20260810-1`.

## 1.6.0 – 2026-08-10 – Modul-API v2 und browserfreundliche Suche

- Projektunabhängige Modul-API v2 mit Capabilities-, Validierungs-, Einzel- und Batch-Endpunkten ergänzt; v1 bleibt unverändert erreichbar.
- Bis zu 100 Suchdefinitionen je Batch, genau ein Quellenpaket je Request und HMAC-SHA256-signierte Fortsetzungstoken mit zwei Stunden Laufzeit umgesetzt.
- Quellenneutrale Listing-IDs, explizite Preis-/Versandsemantik und normalisierte Quellenstatus samt Wiederholbarkeit eingeführt.
- Maschinenlesbare OpenAPI-3.1-Dokumentation sowie Vertrags-, Sonderzeichen-, Manipulations-, Ablauf- und Fehlerstatus-Tests ergänzt.
- Weboberfläche auf Modul-v2 umgestellt und Suchbegriff, Plattformwahl und Primäraktion zu einer klaren Suchzeile zusammengeführt.
- Pflicht-, Ausschluss-, Varianten- und Markenbegriffe als entfernbare Chips mit Komma-, Enter- und Einfügeunterstützung umgesetzt.
- Suchkriterien, technische Optionen und Ergebnisfilter deutlicher getrennt; Quellenfortschritt, aktive Filterchips, letzte Suchen und Profilvorschau ergänzt.
- Mobile Filtersteuerung, bekannte-Gesamtsumme-/Favoritenfilter und Favoriten-zuerst-Sortierung ergänzt; Kartenstatus als „Passend“, „Prüfen“ und „Unpassend“ benannt.
- Keine Katalog-, Sammlungs-, Marktwert-, Deal- oder persistenten Serverjob-Modelle in GenericParser aufgenommen.
- Suchkern, Kleinanzeigen-Pagination, Vinted Service Binding, eBay Browse API, Produktklassifizierung, Modul-v1, explizite Favoriten und signierter eBay-Löschendpunkt kompatibel beibehalten.
- Rollback-Ziel: 1.5.1 / `gp-151-20260810-1`.

## 1.5.1 – 2026-08-10 – Wahrheitsgemäßer Stoppstatus und GUI-Politur

- Manuellen Stopp nicht mehr als „vollständig beendet“, sondern als pausierten, gespeicherten und fortsetzbaren Suchstand dargestellt.
- `search_stopped` mit `complete:false`, Grund und Fortsetzbarkeit protokolliert; alte und neue Stoppereignisse werden im Eventlog eindeutig dargestellt.
- Ergebnisfilter auf Desktop in zwei vollständig gefüllte Reihen gegliedert und für Tablet, Mobiltelefon sowie sehr schmale Ansichten responsiv abgestuft.
- Filterbereich mit ruhigerer Flächenhierarchie, klarer Fokusdarstellung und sichtbarem Standard „Rot ausgeblendet“ aufgewertet.
- Kartenhierarchie, Favoriten, Standardfilter, Klassifizierung, Quellenlogik, Modulvertrag und Kleinanzeigen-Suchkern unverändert beibehalten.
- Rollback-Ziel: 1.5.0 / `gp-150-20260810-1`.

## 1.5.0 – 2026-08-10 – Produktklassifizierung, Filter und Favoriten

- Erklärbare Produktklassifizierung für Hauptprodukte, Zubehör/Ersatzteile, Bundles, Gesuche, Vermietung, Dienstleistungen, Merchandise und unklare Treffer ergänzt.
- Bekannte Fehlertreffer aus dem Produktionslauf – Ravensburger-Kartenspiele, Jakks-Figuren und Carrera-Spielzeug – als unpassendes Merchandise klassifiziert.
- Evercade-, SNES- und durch eBay-Kategorien bestätigte Videospiele als Hauptprodukte erkannt; unsichere Zuordnungen bleiben gelbe Prüffälle.
- Ampelgruppen fest in der Reihenfolge Grün, Gelb, Orange, Rot sortiert; die Nutzersortierung wirkt innerhalb der Gruppen.
- Ergebnisfilter für Ampel, Quelle, Produktart, Zustand, Gesamtpreis, Versand, Einzelangebot/Bundle und Angebotsart ergänzt; Rot standardmäßig ausgeblendet.
- Anzeigentext aus den Karten entfernt und das dekorative Symbol auch aus `Log & Diagnose` entfernt.
- Sternaktion und Unterseite `Favoriten` ergänzt. Favoriten werden nur nach ausdrücklicher Auswahl im aktuellen Browser gespeichert und enthalten keine Beschreibung oder Verkäufer-/Kontodaten.
- Separaten eBay Marketplace Account Deletion Worker ergänzt: SHA-256-Challenge, ECDSA-Signaturprüfung über eBays Public-Key-API und datensparsame Bestätigung gültiger Meldungen.
- Kleinanzeigen-Referenzkern, Vinted Service Binding, eBay Browse API, Versand-Gesamtpreis und `generic-parser-module-v1` beibehalten.
- eBay-Production-Zugangsdaten nach der Rotation erneut live geprüft; Browse Search auf `EBAY_DE` antwortete mit HTTP 200. Die Marketplace-Account-Deletion-Ausnahme wurde deaktiviert und Endpoint-Validierung sowie Testbenachrichtigung wurden betreiberseitig bestätigt.
- Produktionsabnahme erfolgreich: Workflow `31361068931` (Versuch 2) bestätigte auf Commit `33931e0dd391c68539ec1965342eff8a40d77070` Challenge-Vertrag und Secret-Bindings, 7 Kleinanzeigen-, 25 Vinted- und 25 eBay-Treffer, 57 von 57 klassifizierte Treffer, 25 konsistente bekannte eBay-Gesamtsummen, ausschließlich Festpreisangebote im Standardlauf, keine Verkäufer-/Kontodaten und einen vollständigen Vinted-Detailbatch mit 3 von 3 Treffern.
- Rollback-Ziel: 1.4.0 / `gp-140-20260809-1` / Commit `7eb1b9c6a124ee43f36555cfca7bce39ddd1e47c`.

## 1.4.0 – 2026-08-09 – eBay Production Browse API

- eBay Deutschland über die offizielle Browse API als dritte Standardquelle ergänzt.
- Application-OAuth per `client_credentials` mit ausschließlich im Worker-Speicher gehaltenem Token-Cache umgesetzt.
- Festpreisangebote bleiben Standard; reine Auktionen sind nur über `include_ebay_auctions` aktivierbar.
- Artikelpreis, Versandkosten und Gesamtpreis getrennt normalisiert. Der bestehende Bewertungswert `price` wird nur gesetzt, wenn der Gesamtpreis einschließlich Versand verlässlich bekannt ist.
- Unbekannte Versandkosten in API und Browser sichtbar gelassen, statt einen irreführend niedrigen Gesamtpreis zu bewerten.
- eBay-Treffer aus IndexedDB-Exporten ausgeschlossen und serverseitig nicht persistiert.
- Bestehenden Kleinanzeigen-Kern, Vinted Service Binding, begrenzte Detailanreicherung und Modulvertrag beibehalten.
- Einmaliger Production-Zugriffstest erfolgreich: OAuth und Browse Search auf `EBAY_DE` antworteten im Workflow `31336200661` mit HTTP 200.
- GitHub-Secrets im Deployment ausschließlich über stdin in verschlüsselte Cloudflare Worker Secrets synchronisiert; keine Ausgabe und keine normalen Wrangler-Variablen.
- Produktionsabnahme erfolgreich: Workflow `31337634699` bestätigte auf Commit `7eb1b9c6a124ee43f36555cfca7bce39ddd1e47c` die Live-Identität, Secret-Bindings, 7 Kleinanzeigen-, 25 Vinted- und 25 eBay-Treffer, 25 konsistente bekannte eBay-Gesamtsummen, ausschließlich Festpreisangebote im Standardlauf sowie einen vollständigen Vinted-Detailbatch mit 3 von 3 Treffern.
- Rollback-Ziel: 1.3.4 / `gp-134-20260809-1` / Commit `47a74efa13f63b0908688cc96872e013f23e56bf`.

## 1.3.4 – 2026-08-09 – Dichtes Ergebnisraster

- Trefferkarten erheblich verkleinert und in ein responsives Mehrspaltenraster überführt.
- Auf üblichen Desktopbreiten mindestens drei, auf breiten Bildschirmen vier bis fünf Karten nebeneinander vorgesehen.
- Bild und Text innerhalb jeder Karte dauerhaft nebeneinander angeordnet, auch auf Mobilgeräten.
- Vorschaubild auf eine kleine quadratische Medienfläche reduziert und Abstände, Badges, Preis, Metadaten sowie Aktion proportional verdichtet.
- Dekoratives Vier-Punkte-Symbol im linken Kopf der Startseite entfernt.
- Vierzeilige Vinted-Beschreibung, Aufklappen, Hashtag-Bereinigung, Log-Navigation und übrige 1.3.3-Oberfläche beibehalten.
- Suchkern, Matching, Ampel, Pagination, Vinted-3er-Batches, Modulvertrag und Worker-Endpunkte unverändert belassen.
- Produktionsabnahme erfolgreich: Worker-Identität, dichtes responsives Kartenraster, Kleinanzeigen-plus-Vinted-Suche und entkoppelter Vinted-Detail-Batch liefen auf Commit `47a74efa13f63b0908688cc96872e013f23e56bf` im Workflow `31311244612` grün durch; Rückfallziel bleibt 1.3.3 / `gp-133-20260809-1`.

## 1.3.3 – 2026-08-09 – GUI-Rework und kompakte Vinted-Karten

- Kopfbereich an die aktuellen Evercade- und SNES-Oberflächen angelehnt.
- Versionsbadge und direkter Einstieg zu `Log & Diagnose` in den oberen Seitenkopf verschoben.
- Erklärende Release-Texte und den sichtbaren Schalter `Technische Details anzeigen` aus der Suchoberfläche entfernt.
- Suchprofil, Statusbereiche und Aktionen auf ein ruhigeres, responsives Panelraster umgestellt.
- Ergebnisdarstellung an das SNES-Angebotsraster angelehnt: größere Vorschaubilder, eindeutige Quellen- und Ampelbadges sowie eine primäre Aktion pro Karte.
- Vinted-Beschreibungen standardmäßig auf vier Zeilen begrenzt und über `Mehr anzeigen` vollständig aufklappbar gemacht.
- Reine Hashtag-Zeilen und lange angehängte Hashtag-Ketten aus Vinted-Beschreibungen ausgeblendet; ausschließlich aus Hashtags bestehende Beschreibungen erscheinen nicht mehr als leere Langkarten.
- Aufgeklappte Beschreibungen bleiben bei nachgeladenen Vinted-Hintergrunddetails erhalten.
- Hauptsuche, Matching, Scoring, Pagination, Vinted-3er-Batches, Modulvertrag und Worker-Endpunkte unverändert belassen.
- Produktionsabnahme erfolgreich: Worker-Identität, responsive UI-Verträge, Kleinanzeigen-plus-Vinted-Suche und entkoppelter Vinted-Detail-Batch liefen auf Commit `88df0a4f91fd813a685e26b429e3c549bb9ce5b3` im Workflow `31306994225` grün durch.
- Rollback-Ziel: 1.3.2 / `gp-132-20260809-1` / `cece9c4723eca97fb38627493628468b21e5fb86`.

## 1.3.2 – 2026-08-09 – Entkoppelte Vinted-Detailanreicherung

- Den stabilen 1.3.1-Katalogpfad und dessen Limit von drei Inline-Detailseiten unverändert beibehalten.
- Fehlende Vinted-Details nach der Katalogantwort in seriellen Hintergrund-Batches mit je höchstens drei parallelen Detailseiten ergänzt.
- Additive Endpunkte `/api/vinted/enrich` und `/api/module/v1/vinted/enrich` eingeführt.
- Ausschließlich kanonische Vinted-HTTPS-Item-URLs mit passender Listing-ID für Detailabrufe zugelassen.
- Nachgeladene Bilder, Preise, Beschreibungen und Zustände in bestehende Treffer gemischt.
- Preisabhängiges Matching und Ampelbewertung nach jedem Detail-Batch erneut ausgeführt.
- Browser-Warteschlange bei Nutzerstopp oder neuer Suche sauber beendet; Hauptsuche wartet nie auf Hintergrund-Batches.
- Sichtbare Vinted-Detailfortschrittsanzeige und vollständige Batch-Ereignisse im Eventlog ergänzt.
- Modulantworten erhalten `description`, `source_label` und `detail_enrichment` jetzt ausdrücklich.
- Kleinanzeigen-Suchkern, Pagination, Paid-Worker-Zeitprofil, Modulvertrag sowie Evercade-/SNES-Adapter unverändert belassen.
- Produktionsabnahme erfolgreich: Worker-Identität, Kleinanzeigen-plus-Vinted-Suche und entkoppelter Vinted-Detail-Batch liefen auf Commit `cece9c4723eca97fb38627493628468b21e5fb86` grün durch.
- Rollback-Ziel: 1.3.1 / `gp-131-20260809-1` / `506bdd234304e215ca77ae58f217f6217c5a206c`.

## 1.3.1 – 2026-08-09 – Begrenzte Vinted-Detailanreicherung

- Vinted-Katalogabruf auf 15 Sekunden und Detailnavigation auf 6 Sekunden begrenzt.
- Pro Katalogseite höchstens drei Detailseiten parallel geöffnet.
- Übrige Treffer als `skipped_budget` ohne Blockade der Seitensuche zurückgegeben.
- Live bestätigt: 10 Requests, 162 Ergebnisse, vollständiger Abschluss ohne 49-Sekunden-Abbruch.

## 1.3.0 – 2026-08-09 – Vinted-Detaildaten

- Bild, Preis, Beschreibung und Zustand aus Vinted-Detailseiten ergänzt.
- Multi-Source-Diagnose und Vinted-Scoring erweitert.
- Live-Regression: vollständige Inline-Anreicherung blockierte den Hauptrequest bis zum Abbruch nach rund 49 Sekunden; durch 1.3.1 ersetzt.

## 1.0.0 – 2026-08-08 – Stable

- Den funktionierenden GenericParser 0.45.2 Build 7 Paid Worker als erste stabile Produktionsversion freigegeben.
- Versionsschema ab jetzt auf Semantic Versioning umgestellt.
- API-/Modulvertrag `generic-parser-module-v1` unverändert übernommen.
- Evercade- und SNES-PAL-Adapter unverändert übernommen.
- Suchruntime bleibt `0.45.0`, fachlicher Suchkern `0.44.4`, operative Referenz `0.44.6.5`.
- 7er-Arbeitspakete, Pagination, Extraktion, Matching, Scoring und Ampel nicht verändert.
- Free-Worker-Schutzzeiten bleiben im Paid-Worker-Profil deaktiviert: kein Such-Cooldown, keine normale Paketpause, keine Retry-Wartezeiten.
- Health, Version, Diagnostics, CORS/OPTIONS und alle Suchalias-Routen bleiben Bestandteil der Produktionsabnahme.
- Browser-/Worker-Identität, Paketmetadaten, README, Roadmap, Release-Dokumentation und Deploy-Workflow auf 1.0.0 vereinheitlicht.
- Eigene 1.0.0-Regressionssuite und Live-Deployment-Gate ergänzt.
- Letzter Rollback-Stand vor 1.0: 0.45.2 Build 7 Paid Worker, Commit `70c22ee4cda2f029490fb6825668db57358e4aa5`.

## 0.45.0 – 2026-08-05 – Modulversion

- Stabilen Vertrag `generic-parser-module-v1` für eingebettete Projekte eingeführt.
- Projektneutrale Profile, Listings, Pagination und Summary in `module_api.py` ergänzt.
- Neue Endpunkte `/api/module/v1/capabilities`, `/profile/validate`, `/search` und `/self-test` bereitgestellt.
- Bestehenden `/api/search`-Pfad und den 0.44.4-Suchkern funktional unverändert aus 0.44.6.5 übernommen.
- Evercade- und SNES-PAL-Profiladapter ergänzt.
- Leere optionale Profilfelder werden vor der Übergabe an den Referenzkern entfernt.
- Debug-Logs als standardmäßig deaktivierten Browser- und Request-Schalter ergänzt.
- Payloadlogging bleibt auch im Debugmodus standardmäßig deaktiviert.
- Netzwerkfreie Modul-Selbsttests ergänzt; standardmäßig deaktiviert und nur explizit ausführbar.
- Mobile Oberfläche um getrennte Schalter für Debug-Logs und Modultests erweitert.
- Modulbezogenes Eventlog und CI-Regressionssuite ergänzt.
- Alte 0.44.6.6-Experiment-Suite auf ausschließlich manuelle Ausführung umgestellt.
- 0.44.6.5 bleibt die stabile Rückfallreferenz; Cloudflare-Live-Abnahme steht aus.

## 0.44.6.6.1 – 2026-08-05 – verworfenes Testexperiment

- Live-Befund aus 0.44.6.6 Build 3 übernommen: eine 90-Sekunden-Testpause wurde ausgeführt, die Suche erreichte anschließend 230 Ergebnisse und Seite 35.
- Geplante Browserpause bei 120, 240, 360 und jedem weiteren Vielfachen von 120 eindeutigen Treffern von 90 auf 120 Sekunden erhöht.
- Recovery-Ruhezeit nach einer terminalen 503-/1101-Kette ebenfalls von 90 auf 120 Sekunden erhöht.
- Bekannten Recovery-Abbruch `resume_control_unavailable` behoben: Die Fortsetzen-Schaltfläche wird nach erfolgreicher Worker-Prüfung sichtbar und aktiv gesetzt.
- Nach dem ersten automatischen Fortsetzungsversuch wird zehn Sekunden auf ein `search_resume`-Ereignis gewartet.
- Fehlt dieses Ereignis, wird die Fortsetzen-Steuerung genau einmal erneut ausgelöst und als `auto_resume_control_retry` protokolliert.
- Live-Befund: Fortsetzungen wurden gestartet, scheiterten aber unmittelbar erneut mit 1101 vor ASGI beziehungsweise HTML-503.
- Weitere Browser-Recovery-Experimente wurden beendet; 0.44.6.5 bleibt Referenz.

## 0.44.6.6 Build 3 – 2026-08-04 – Testversion

- Fehler aus Build 2 analysiert: `countdown()` liegt in `app.js`, wurde aber fälschlich per Textanker in `controller-0411.js` gesucht.
- Den aktiven Controllerfluss wieder auf die funktionierende Struktur von 0.44.6.5 zurückgeführt.
- Cooldown als separates Skript `cooldown-04466.js` nach `app.js` und vor dem Controller eingebunden.
- Testlogik fail-open ausgeführt: Kann der Cooldown nicht initialisiert werden, bleibt die 0.44.6.5-Suche aktiv.
- Normale Seitenpause wird bei 120, 240, 360 und jedem weiteren Vielfachen von 120 eindeutigen Treffern durch 90 Sekunden ersetzt.
- Retry-Wartezeiten, Search-Service, Workerpfad, Pagination, 7er-Pakete, Ampel und Recovery bleiben unverändert.
- Laufzeitprüfungen für den Referenzcontroller, die Schwellen 120/240 und das Fail-open-Verhalten ergänzt.
- 0.44.6.5 bleibt bis zum Live-Test die stabile Referenz.

## 0.44.6.6 Build 2 – 2026-08-04 – verworfene Testversion

- Stabile Referenz 0.44.6.5 sollte vollständig beibehalten werden.
- Build 1 war nur in Metadaten als Cooldown-Test sichtbar; im aktiven Controller fanden keine Testpausen statt.
- Build 2 sollte die normale Seitenpause bei 120, 240, 360 und jedem weiteren Vielfachen von 120 eindeutigen Treffern durch 90 Sekunden ersetzen.
- Live-Regression: Controllerstart scheiterte mit `Reference countdown anchor missing`; Suche blieb gesperrt.
- Ursache: Die Pausenfunktion wurde im falschen Referenzskript gesucht.
- Build 2 wurde durch Build 3 ersetzt.

## 0.44.6.5 – 2026-08-04 – stabile Rollback-Referenz

- Technischer Rückbau auf das bestätigte Verhalten von 0.44.6.2.
- Worker-Einstieg, FastAPI-Bootstrap, Controller und einmalige 90-Sekunden-Fehler-Recovery aus der Referenzlinie wiederhergestellt.
- Unveränderter 0.44.4-Suchkern mit 7er-Arbeitspaketen, 5-Sekunden-Pause und echter Weiter-Navigation.
- Recovery-Probes und zwei Auto-Resume-Zyklen aus 0.44.6.3 deaktiviert.
- Lazy-ASGI-Bootstrap aus 0.44.6.4 deaktiviert.
- Live bestätigt: Rollback funktioniert.

## 0.44.6.4 – 2026-08-04 – verworfenes Experiment

- Leichten direkten Versions- und Recovery-Probe-Einstieg mit Lazy-ASGI-Import getestet.
- Regression im Live-Test: erste Suche scheiterte bereits auf Seite 0 mit 503/1101 und 0 Ergebnissen.
- Version verworfen und durch 0.44.6.5 zurückgebaut.

## 0.44.6.3 – 2026-08-04 – verworfenes Recovery-Experiment

- Arbeitsreferenz 0.44.6.2 beibehalten und den 0.44.4-Suchkern unverändert delegiert.
- Neuen Endpunkt `/api/recovery-probe` ergänzt, der Python-Runtime, Search-Service, Request-Modell, Suchfunktion und Referenzkern prüft, ohne Kleinanzeigen aufzurufen.
- Recovery-Trigger um Cloudflare 1102 erweitert und `cf-error-type`, `cf-error-origin`, `Retry-After` und Ray-ID protokolliert.
- Gestaffeltes Recovery-Backoff von 90, 180 und 360 Sekunden mit ±10 Prozent Jitter eingeführt.
- Probe-Wiederholungen nach 30, 60 und 120 Sekunden; höchstens drei Probes je Zyklus.
- Höchstens zwei automatische Fortsetzungen je Suchkette; danach manueller Fallback.
- Live-Befund: Recovery-Probe blieb wiederholt mit HTTP 500 hängen; Linie verworfen.

## 0.44.6.2 – 2026-08-04

- Einmalige automatische Fortsetzung nach einer terminalen 503/1101-Fehlerkette ergänzt.
- Trigger nur bei `search_end` mit `retry_exhausted` und bestätigtem Cloudflare 1101 oder mindestens zwei unterschiedlichen HTML-503-Requests.
- 90 Sekunden Ruhezeit vor der ersten Worker-Bereitschaftsprüfung.
- Bis zu vier `/api/version`-Prüfungen im Abstand von 15 Sekunden.
- Fortsetzung verwendet den bereits vorhandenen persistenten Suchstand und die bestehende Resume-Funktion.
- Höchstens ein automatischer Resume je Suchkette; danach bleibt nur manuelles Fortsetzen.
- Suchkern, Pagination, Extraktion, Ampellogik, 7er-Pakete und 5-Sekunden-Pause bleiben unverändert auf Referenz 0.44.4.
- Live-Test: 34 erfolgreiche Arbeitspakete und 219 gespeicherte Ergebnisse vor der nächsten 503/1101-Kette.

## 0.44.6.1 – 2026-08-04

- Falsche Versionsabweichung im Referenzmodus beseitigt.
- Versionsprüfung auf Version, Build und API-Vertrag begrenzt.
- Fehlendes erweitertes Diagnoseschema korrekt als optional dargestellt.
- HTML-503 verständlich als temporären Abruffehler eingeordnet.
- Live-Test: neun erfolgreiche Arbeitspakete, 60 gespeicherte Ergebnisse, danach 503 und Cloudflare 1101 vor ASGI.

## 0.44.6 – 2026-08-04

- Funktionaler Rückbau auf den vollständigen 0.44.4-Referenzkern.
- Experimentelle Parser- und Cursorlogik aus 0.44.5.x nicht mehr verwendet.
- Live-Test: 184 eindeutige Ergebnisse und mindestens 29 erfolgreiche Arbeitspakete.
- Preise, Bilder, Ampel und echte Weiter-Navigation wiederhergestellt.

## 0.44.5 bis 0.44.5.2 – 2026-08-04

- Direkten Standardbibliothek-Worker als Free-Tarif-Experiment umgesetzt.
- Import-/ASGI-Fehler in kurzen Läufen reduziert.
- Funktionale Abdeckung der Referenz jedoch nicht erreicht; Linie als Experiment verworfen.

## 0.44.4 – 2026-08-03

- Ampelbewertung auf tatsächlich gesetzte Felder und aktive Optionen begrenzt.
- Leere Pflicht-, Ausschluss-, Modell-, Marken- und Preisfelder werden ignoriert.
- Funktionale Referenz für Suchfluss, Pagination, Extraktion und Ampel.

## 0.42.7 – 2026-08-03

- Cloudflare-Trace als eindeutige Ursache ausgewertet: `Worker exceeded CPU time limit`.
- Free-Tarif-Pfad vollständig auf kleine virtuelle Arbeitspakete umgestellt.
- Eine Kleinanzeigen-Quellseite wird in bis zu vier Pakete mit höchstens sieben Karten zerlegt.
- Vollständige BeautifulSoup-DOM-Rekonstruktion und schweres Legacy-Scoring aus dem produktiven Free-Pfad entfernt.
- Browser wartet fünf Sekunden zwischen den Paketen und speichert nach jedem Paket den Suchstand.
- Technischer Abschluss-Commit: `119a05985d11017940b775bb2c6cc7bc6acd992a`.

## 0.42.6 – 2026-08-02

- Experimentellen FFI-Transport zurückgenommen.
- Eigenständigen minimalen Readiness-Bootstrap eingeführt.
- `/api/version` von Search-Service-Importen entkoppelt.
- Cloudflare-Observability zur Diagnose des tatsächlichen Laufzeitfehlers genutzt.

## 0.42.5 – 2026-08-02

- Experimenteller Workers-Fetch über Python-JavaScript-FFI.
- Die Änderung erwies sich im Live-Betrieb als Regression und wurde in 0.42.6 entfernt.

## 0.42.4 – 2026-08-02

- Gemeinsame Build-Identität für Suchseite, Controller, Handshake, Worker und Eventlog eingeführt.
- Das Eventlog prüft seine Version und Build-ID beim Öffnen gegen `/api/version`.
- Das Eventlog verwendet einen eigenen 0.42.4-Speicherschlüssel.
- Produktionsstand: `0.42.4` / `gp-0424-20260802-1` / `match-v6.1-page-worker`.

## 0.42.3 – 2026-08-02

- Pagination beendet die Suche, sobald `reported_total` erreicht ist.
- Kurze HTML-Ergebnisseiten werden als Abschluss erkannt.
- Unnötige Folgeseiten und dadurch ausgelöste 503/1101-Ketten werden vermieden.
- Technischer Abschluss-Commit: `9c8841fecac53ffaa127a7ed83ca94492a260a88`.

## 0.42.2 – 2026-08-02

- Suchlogik aus älteren FastAPI-Worker-Apps herausgelöst.
- App-freier Ein-Seiten-Search-Service eingeführt.
- Nur der 0.42.2-Bootstrap besitzt Routen und Middleware.
- Konsistenzprüfung für abgerufene, sichtbare und ausgeblendete Treffer ergänzt.

## 0.42.1 – 2026-08-02

- Suchbutton nach erfolgreichem Handshake zuverlässig aktiviert.
- Zentraler UI-Zustand für Booting, Idle und Blocked.
- Eventlog um Button- und Zustandswechsel erweitert.

## 0.42.0 – 2026-08-02

- Minimaler Lazy-Bootstrap eingeführt.
- Versions- und Readiness-Endpunkte ohne Parserimporte.
- Suchmodule erst innerhalb von `/api/search` geladen.
- Strukturierte Import- und Suchphasen ergänzt.

## 0.41.1 – 2026-08-02

- Deployment-Handshake zwischen UI und Worker eingeführt.
- Einheitliche Version, Build-ID und API-Vertrag über Header und JSON.
- Live-Suche bei inkonsistentem Deployment gesperrt.
- Instabile Ressourcen-Middleware aus dem produktiven Pfad entfernt.

## 0.41.0 – 2026-08-02

- Ressourcenmessungen pro Seite ergänzt.
- Gesamt-, CPU-, Fetch- und Parsezeiten protokolliert.
- Antwortgrößen und Kartenanzahl dokumentiert.

## 0.40.9 – 2026-08-02

- HTML-Fallback in serverseitige Diagnosephasen aufgeteilt.
- UI-Überlappungen und lange Eventlog-Zeilen korrigiert.
- Synthetische Fehlerantworten versionskonsistent gemacht.

## 0.40.8 – 2026-08-02

- Seitennummer, Request-ID, Payload, Fetch-/Parse-Marker und Antwortgrößen ins Eventlog aufgenommen.

## 0.40.7 – 2026-08-02

- Overlay-Controller entfernt.
- Start, Stopp, Fortsetzen und Cooldown in einen Controller zusammengeführt.
- Eventlog gedrosselt.

## 0.40.6 – 2026-08-02

- Sanfter Suchstopp eingeführt.
- Eigene Eventlog-Unterseite ergänzt.

## 0.40.5 – 2026-08-02

- Diagnosephasen, Ray-ID und Laufzeitinformationen für Workerfehler ergänzt.

## 0.40.4 – 2026-08-02

- Cloudflare-1101-Erkennung ohne automatische Retry-Schleife.
- Worker-Pfad auf stabileren Seitenworker zurückgeführt.

## 0.40.3 – 2026-08-02

- Integrierte Session-Steuerung für Start, Stopp und Folgesuchen.
- Alte Requests und Retries von neuen Suchsessions getrennt.

## 0.40.2 und frühere 0.3x/0.4x-Zwischenstände

- Aufbau der seitenweisen Suche, Pagination, Deduplizierung, Fortsetzung, Workerstatus und mobilen PWA.
- Die vollständigen Einzeländerungen bleiben über die Git-Historie nachvollziehbar.

## 0.2.0rc2 – 2026-08-01

Produktionsreifes Cloudflare-Deployment für Meilenstein 0.2d.

## 0.2.0rc1 – 2026-08-01

Mobile Cloudflare-Worker/PWA-Version für manuelle Kleinanzeigen-Diagnose.

## 0.2.0b1 – 2026-08-01

Diagnose-Webinterface für manuelle und reproduzierbare Parserprüfungen.

## 0.2.0a1 – 2026-08-01

Erster Kleinanzeigen-Ergebnislistenadapter.

## 0.1.0 – 2026-08-01

Erster abgeschlossener Bibliothekskern mit Datenmodellen, Normalisierung, Konfiguration, Serviceklasse und Beispielprofilen.
