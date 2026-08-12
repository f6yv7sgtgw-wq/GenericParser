# Changelog

Die Einträge fassen die produktiven Entwicklungsstände zusammen. Einzelne Versionen bestehen aus mehreren technischen Commits; der Abschluss-Commit steht in `docs/RELEASE_INDEX.md`.

## 1.8.9 – 2026-08-12 – Zwei verlorene Assets und ein Log, das den Lauf beschreibt

- Das 1.6.5-Aufräumen entfernte **zwei Browser-Assets, die sehr wohl geladen werden** — über zusammengebaute `fetch`-Pfade, die eine statische Erreichbarkeitsanalyse nicht sieht. Genau die Falle, vor der derselbe Changelog-Eintrag bei den per `importlib` geladenen Python-Modulen noch gewarnt hatte.
- `auto-resume-04462.js` wiederhergestellt: Ohne sie brach `auto-resume-0450.js` bei jedem Seitenaufruf mit `0.44.6.2 recovery key fragment missing` ab, die automatische Wiederaufnahme war seit 1.6.5 tot.
- `controller-0411.js` wiederhergestellt: Ohne sie scheiterte `loadControllerSource()`, und damit unterblieb der gesamte `.then()`-Block — **einschließlich der Abschaltung der Latenzdrosselung**. Das war der Fünf-Sekunden-Timer, den 1.8.6 behandelt hat; hier liegt seine eigentliche Ursache.
- Beide Fehler waren unsichtbar, weil das Eventlog bis 1.8.8 niemanden hatte, der es beschrieb.
- Neuer Test prüft **jeden** per `new URL('./…')` zusammengebauten Asset-Pfad gegen das Dateisystem. Er fand `controller-0411.js` unmittelbar nach dem Wiederherstellen von `auto-resume-04462.js`.
- Das Log beschreibt jetzt einen Lauf: `search_started` mit Suchbegriff und Quellen, `search_packet` je Paket mit Quelle, Seite, Trefferzahl und Laufzeit, `search_finished` mit Bilanz je Quelle. Das Ende wird auch bei manueller Pause und bei Abbruch geschrieben — vorher entstand nur ein Eintrag, wenn etwas schiefging.
- Die Aufklappzeile „Warum?" entfällt bei passenden Treffern und bleibt bei Prüf- und Ablehnfällen, wo die Begründung trägt.
- Neue Suite `tests/test_release_189.py` (6).
- Produktionsabnahme: ausstehend. Rollback-Ziel: 1.8.8 / `gp-188-20260812-1`.

## 1.8.8 – 2026-08-12 – Der fehlende Log-Schreiber

- **Das Eventlog war nie befüllt.** Jeder Aufrufer prüfte nur `typeof window.gpEventLog === 'function'`, und die Log-Seite las einen Speicher, den niemand beschrieb. Alle Log-Aufrufe im Suchpfad waren wirkungslos — auch die in 1.8.7 ergänzten `source_finished`-Einträge. Der Download aus 1.8.7 konnte damit nur „Log ist leer" melden.
- `eventlog-writer-188.js` liefert den Schreiber nach und wird auf Such- und Log-Seite vor allen Aufrufern geladen. Ein bereits vorhandener Schreiber wird nicht verdrängt.
- Das Log ist auf 800 Einträge begrenzt. Ein voller Speicher wirft die ältere Hälfte weg, statt eine laufende Suche abzubrechen; eine nicht serialisierbare Nutzlast kostet den Eintrag nicht.
- **`fixed_price` stand roh in der Kachel.** `listingFromV2` reichte den Modul-v2-Code als Anzeigetext durch. Angebotsformate erscheinen jetzt als „Festpreis", „Auktion" und „Preisvorschlag" — die Bezeichnungen sind so gewählt, dass der Angebotsart-Filter sie weiterhin richtig einordnet.
- Neue Suiten `tests/js/eventlog-writer-188.test.mjs` (5) und `tests/test_release_188.py` (5).
- Produktionsabnahme erfolgreich: Deploy-Workflow `31637164241` lief auf Commit `6012f33896da993fa6715c6d2d8af55f31557179` grün durch. Live bestätigt durch zwei heruntergeladene Logdateien mit echten Einträgen — der Download funktioniert, und die Kacheln zeigen `Festpreis` statt `fixed_price`. Rollback-Ziel: 1.8.7 / `gp-187-20260812-1`.

## 1.8.7 – 2026-08-12 – Abbruchgrund je Quelle und Log-Download

- Jede Quelle hält jetzt fest, **warum** sie aussteigt: Status, Grund, Paketzahl und Trefferzahl. Bisher endete ein Lauf ohne Spur davon, ob eine Quelle erschöpft, blockiert, gedrosselt oder in eine Zeitgrenze gelaufen war — beobachtete Obergrenzen wie 64 bei Kleinanzeigen, 110 bei Vinted und über 700 bei eBay ließen sich nur raten.
- Der Grund steht in der Diagnose der Suchseite und wird als `source_finished` ins Eventlog geschrieben — einmal je Quelle, nicht bei jedem weiteren Paket.
- Die bekannten Zustände sind in Klartext benannt (`blocked` → „von der Quelle blockiert", `rate_limited` → „von der Quelle gedrosselt", `empty` → „keine weiteren Treffer" und so fort).
- Das Eventlog lässt sich als JSON-Datei herunterladen. „Log kopieren" reicht nicht, wenn ein Lauf über hunderte Einträge geht oder das Ergebnis weitergegeben werden soll.
- Der Export trägt Version, Build-ID, Identitätsquelle, Exportzeit und Eintragszahl mit, damit ein später gelesenes Log einem Stand zuzuordnen ist.
- Der Dateiname enthält keine Doppelpunkte, die Windows in Dateinamen ablehnt; der Blob wird nach dem Download wieder freigegeben.
- Ein leeres Log meldet das, statt eine leere Datei zu schreiben; ein beschädigter Speicher liefert eine leere Liste, statt den Export abzubrechen.
- Neue Suiten `tests/js/source-outcome-187.test.mjs` (5), `tests/js/eventlog-export-187.test.mjs` (6) und `tests/test_release_187.py` (4).
- Produktionsabnahme: ausstehend. Rollback-Ziel: 1.8.6 / `gp-186-20260812-1`.

## 1.8.6 – 2026-08-12 – Drosselung entschärft

- Der Fünf-Sekunden-Timer war keine Kleinanzeigen-Pause, sondern die latenzabhängige Drosselung `adaptiveDelay`: Ab vier Sekunden Paketlaufzeit wartete der Lauf danach fünf Sekunden.
- Abgeschaltet werden sollte sie längst — `controller-0450.js` setzt `adaptiveDelay = () => 0` und `countdown = async () => {}`. Diese Zuweisung sitzt aber in einem `.then()`: Schlägt das Laden der Controller-Quelle oder eines der Ersetzungsmuster fehl, unterbleibt sie stillschweigend und die Drosselung ist wieder scharf. `app.js` entscheidet das jetzt selbst anhand von `workerPlan` und `protectionDelays` aus der Build-Identität.
- Fehlt die Identität ganz, bleibt die Drosselung vorsichtshalber aktiv.
- Während die Quellen rotieren, entfällt die Pause zwischen Paketen vollständig. Sie war ein einziger Wert für den gesamten Lauf: Seit 1.8.5 konnte damit ein langsames Vinted- oder eBay-Paket fünf Sekunden Wartezeit vor dem nächsten **Kleinanzeigen**-Paket erzwingen — die langsamste Quelle bremste alle übrigen aus. Der Turnus sorgt selbst für den Abstand, weil bis zur nächsten Runde einer Quelle die anderen bedient wurden.
- Bei einer Suche auf genau eine Quelle bleibt die Drosselung als Schutz erhalten.
- Neue Suite `tests/js/throttle-186.test.mjs` (6) und `tests/test_release_186.py` (4).
- Produktionsabnahme erfolgreich: Deploy-Workflow `31631370116` lief auf Commit `18118a163695378ad14d2b9ddc60a80a4433ac26` grün durch — im zweiten Anlauf, nachdem der erste am Pyodide-Download von GitHub gescheitert war (`http2 error: refused stream`, reine Netzwerkstörung). Der Fünf-Sekunden-Timer tritt produktiv nicht mehr auf. Rollback-Ziel: 1.8.5 / `gp-185-20260812-1`.

## 1.8.5 – 2026-08-12 – Quellen im Turnus und geteilte Fallsammlung

- Die Quellen wechseln sich jetzt ab: nach jeder verarbeiteten Seite ist die nächste noch offene Quelle an der Reihe. Bisher wurde Kleinanzeigen vollständig ausgelesen, dann Vinted, dann eBay — ein gemischtes Ergebnisbild entstand erst spät oder gar nicht, wenn der Lauf vorher gestoppt wurde.
- Jede Quelle führt einen eigenen Seitenzeiger (`source_pages`) und meldet ihr Ende getrennt (`sources_done`). Ohne das könnte die Rotation nicht dort weitermachen, wo eine Quelle stehen geblieben ist.
- Eine erschöpfte Quelle fällt aus dem Turnus; die übrigen laufen ohne Leerlauf weiter. Bei einer Ein-Quellen-Suche bleibt das Verhalten unverändert.
- Fortsetzungstoken aus Läufen vor 1.8.5 tragen die neuen Felder nicht und starten mit leeren Vorgaben; laufende Suchen brechen dadurch nicht ab.
- Die Paketgröße bleibt eine Marktplatzseite je Anfrage — rund 25 Treffer bei allen drei Quellen. Kleiner geht nicht, weil eine Seite die kleinste Abrufeinheit ist; größer würde die Mischung nur verzögern.
- Deterministische Fallsammlung `tests/fixtures/normalization_cases.json` mit 41 Zustands-, 16 Größen-, 12 beschrifteten Größen-, 11 Konvolut- und 7 Versandfällen. Python-Adapter und Vinted-Worker werden gegen dieselbe Datei geprüft.
- Die Sammlung deckte sofort drei echte Lücken auf: „wie-neu" galt wegen des Bindestrichs als **neu** statt `like_new`; `_size_text` kannte die Zwölf-Zeichen-Grenze des Workers nicht und ließ Fließtext als Größe durch; „1.200 €" wurde zu Titel „Konsole 1" mit Preis 200.
- Zustandsangaben werden vor dem Vergleich von Interpunktion befreit, die Regeln enthalten entsprechend keine mehr — ein neuer Test hält das fest.
- Beträge verstehen Tausenderpunkte. Ein Punkt gilt nur bei genau drei Folgeziffern als Trennzeichen, sonst als Dezimalpunkt.
- Produktionsabnahme erfolgreich: Deploy-Workflow `31629667313` lief auf Commit `3486cb4aeb1365ab3b2f0777283e23872f2c70da` grün durch. Live bestätigt: `/health` meldet 1.8.5 / `gp-185-20260812-1`, und ein Lauf über sechs Fortsetzungspakete zeigte den Turnus `kleinanzeigen:0 → vinted:0 → ebay:0 → kleinanzeigen:1 → vinted:1 → ebay:1`. Rollback-Ziel bleibt 1.7.1 / `gp-171-20260812-1`.

## 1.8.1 – 2026-08-12 – Korrekturen aus dem 1.8.0-Livelauf

- Füllwörter für Stückpreise (`je`, `jeweils`, `à`, `Stk.`, `pro Stück`) bleiben nicht mehr im abgeleiteten Artikelnamen stehen; der Livelauf zeigte eine Kachel „Extreme-G 2 je".
- Das Füllwortmuster verlangt ein führendes Leerzeichen. Ohne das verschluckte `à` das Schluss-a von „Zelda".
- `pro Stück` aus der Stoppliste entfernt: Es verwarf echte Artikel wie „Mario Kart pro Stück 20 €". Der gemeinte Fall „Preis pro Stück 20 €" wird weiterhin über `preis pro` abgefangen.
- `offer.derived_from` nennt die Ursprungsanzeige jetzt als vollständigen `listing_key` statt als nackte Anzeigen-ID.
- Keine weiteren Änderungen gegenüber 1.8.0.
- Produktionsabnahme erfolgreich: Deploy-Workflow `31616736358` lief grün durch; der Livelauf `Nintendo 64 Konvolut` lieferte 21 abgeleitete Kacheln ohne Füllwort-Reste und mit vollständigen `listing_key`-Verweisen. Von 1.8.5 in Produktion abgelöst.

## 1.8.0 – 2026-08-12 – Quellenqualität, Konvolutauflösung und neue Suchmaske

- Zustand und Versand werden quellenneutral normalisiert: `normalization.py` liefert stabile Codes, das v2-Schema trägt sie additiv als `condition_code` und `delivery.mode` neben dem unveränderten Anzeigetext. Vorher leitete erst der Browser per Regex einen Code aus dem Anzeigetext ab, ein Zustandsfilter matchte damit faktisch auf Anzeigestrings.
- Dabei zwei Fehlgriffe behoben: „wie neu" galt als **neu**, „Sehr gut" als **gebraucht**. Beide sind jetzt `like_new` mit eigener Filteroption, damit die Treffer nach der Trennung nicht unsichtbar werden.
- Ein Defekt schlägt eine neu klingende Formulierung: „Neu, aber defekt" ist `defective`.
- Kleinanzeigen-Konvolute mit Einzelpreisliste werden in Einzelkacheln aufgelöst. Die Detailseite wird nur für Treffer geholt, die die Klassifizierung ohnehin als Konvolut ausweist — das begrenzt die Kosten von selbst; Budget sind drei Detailseiten je Ergebnisseite.
- Abgeleitete Kacheln sind keine eigenständigen Angebote: Sie tragen die URL der Ursprungsanzeige, verweisen über `offer.derived_from` auf sie und zeigen im Browser ein „aus Konvolut"-Merkmal. Es wird keine URL erfunden.
- Versandzeilen, Neupreise und Gesamtsummen werden nicht zu Artikeln, mehrdeutige Preisspannen ebenso wenig. Unter zwei erkannten Positionen bleibt es bei einer als Konvolut markierten Kachel. Jeder Fehler beim Abruf oder Parsen lässt die Konvolutkachel unverändert stehen.
- Vinted-Katalogkarten liefern jetzt ihr Foto mit. `extractHtmlListings` erzeugte Treffer bisher ganz ohne `image_url`; die Bilder kamen erst über die Detailwarteschlange mit Budget drei, weshalb das Raster spürbar langsam gefüllt wurde. Fremde Hosts, Icons und Tracking-Pixel werden dabei nicht als Foto akzeptiert.
- Neue Suchmaske: große zentrale Suchleiste, Plattformwahl als Segmentleiste über dem unveränderten `<select>`, Filter in einem einklappbaren Panel statt als Dauerraster, Ladeplatzhalter statt leerer Fläche.
- Die aktiven Filter-Chips stehen bewusst außerhalb des einklappbaren Bereichs — sonst wäre nach dem Zuklappen nicht mehr sichtbar, was gerade filtert.
- Ladeplatzhalter erscheinen nur, solange die Trefferliste leer ist; ein Folgeabruf verdeckt bereits gelieferte Treffer nicht.
- Neue Suiten `tests/test_release_180.py` (17) und `tests/js/ui-180.test.mjs` (4).
- Modul-v1 unverändert; alle neuen v2-Felder sind additiv, bestehende Bedeutungen bleiben gleich.
- Produktionsabnahme erfolgreich: Deploy-Workflow `31616043977` und Vinted-Worker-Workflow `31616043940` liefen grün durch; live bestätigt waren 25 von 25 Vinted-Treffern mit Bild im ersten Paket und 21 aufgelöste Konvolutpositionen. Zwei Schönheitsfehler in den abgeleiteten Titeln wurden unmittelbar mit 1.8.1 nachgezogen.

## 1.7.1 – 2026-08-12 – Parallele Vinted-Detailbatches

- Vinted-Hintergrundbatches laufen zu zweit statt streng nacheinander; die Warteschlange wird auf zwei Arbeiter verteilt, die sich dieselbe Queue teilen. Bei 25 Treffern waren das bisher neun serielle Runden, die Wandzeit halbiert sich etwa.
- Obergrenze bewusst bei zwei Batches: sechs gleichzeitige Detailseiten. Die Grenze für gleichzeitige Browser-Rendering-Sitzungen ist hier die Beschränkung, nicht der Client — drei Batches lägen bei neun und würden ganze Läufe durch 429-Antworten gefährden.
- Vorrang der Hauptsuche unverändert: Die `GP_SEARCH_RUNNING`-Prüfung sitzt in der Arbeiterschleife und greift damit für jeden Arbeiter, nicht nur für den ersten.
- Geteilten `AbortController` durch ein Set ersetzt. Bei seriellem Ablauf war ein einzelner Controller korrekt; parallel hätte jeder neue Batch den vorherigen überschrieben und ein Laufwechsel nur noch den zuletzt gestarteten Batch abbrechen können.
- Status 429 gilt jetzt als wiederholbar — einmal, nach 1,5 Sekunden Pause. Übrige 4xx-Antworten bleiben terminal.
- Zähler der laufenden Details von einer einzelnen Batchgröße auf eine Summe umgestellt; die Statuszeile nennt die tatsächliche Aufteilung.
- Neue Suiten `tests/js/vinted-parallel-171.test.mjs` (3) und `tests/test_release_171.py` (5). Der Parallelitätstest misst das Verhalten, nicht die Konstante, und schlägt gegen den seriellen Stand fehl.
- Schema, Modulverträge, Suchsemantik, Adapter und Oberfläche sind gegenüber 1.7.0 unverändert.
- Produktionsabnahme erfolgreich: Deploy-Workflow `31609957226` und Vinted-Worker-Workflow `31609957253` liefen auf Commit `5f7ed1d07b6fd92f2f76f73962f9dd31fb4c5893` grün durch. Live bestätigt: `/health` meldet 1.7.1 / `gp-171-20260812-1`, eine eBay-Suche nach `King Louie` liefert mit `include_auctions` sechs Auktionen unter 25 Treffern und ohne die Option null, das additive `size`-Feld steht auf allen Treffern, und eine Vinted-Suche lieferte Größen bereits aus den Katalogkarten. Der Gerätetest im Browser war erfolgreich. Rollback-Ziel bleibt 1.6.2 / `gp-162-20260810-1`.

## 1.7.0 – 2026-08-12 – Angebotsformat und Größe als Ergebnisfilter

- eBay-Auktionen werden in der Browseroberfläche standardmäßig mitgesucht; der Ergebnisfilter „Angebotsart" steht neu auf `Ohne Auktionen`. Vorher war die Suchoption aus, wodurch der Filterwert „Auktion" bei jeder Standardsuche zwangsläufig null Treffer ergab — bei rund 700 Treffern für `King Louie` ebenso wie bei jeder anderen Suche.
- Auktions-Checkbox bleibt als Ausweg erhalten, ist vorausgewählt und zählt nur noch als aktives Suchkriterium, wenn sie abgewählt wird.
- Anfrage-Defaults der Modulverträge unverändert: `include_auctions` (Modul-v2) und `include_ebay_auctions` (Modul-v1) bleiben `false`, damit Evercade-, SNES-PAL- und andere Modulkonsumenten keine Verhaltensänderung sehen. `ebay_auction_default_off` gilt ab hier nur noch für den Modulvertrag.
- Vinted-Größe über die gesamte Kette geführt: Extraktion im Vinted-Browser-Worker auf Katalogkarte *und* Detailseite, Normalisierung im Adapter, additives Feld `size` in Modul-v2 samt OpenAPI-Beschreibung, Aufnahme in die Hintergrundanreicherung.
- Größe wird nur als kurzes Label akzeptiert; Platzhalter wie `n/a` oder `unbekannt` werden zu `null`. Fließtext nach dem Wort „Größe" ergibt keine Größe — die Wortgrenze allein hätte bei „Größe könnte" das `k` geliefert.
- Eine Detailseite ohne Größe überschreibt eine bereits bekannte Katalogangabe nicht.
- Zwölfter Ergebnisfilter „Größe" als Facette: angeboten werden nur real vorkommende Größen plus `Ohne Größenangabe`. Die Größe erscheint zusätzlich als Chip auf der Ergebniskarte. Das Filterraster wird dadurch gleichmäßig (6 + 3 + 3).
- Quellen ohne strukturierte Größe melden `null` statt eines Füllwerts, damit „Ohne Größenangabe" eine echte Auswahl bleibt und nicht dieselbe Falle aufmacht wie zuvor der Auktionsfilter.
- Neue Testsuiten `tests/test_release_170.py` (9) und `tests/js/vinted-size-170.test.mjs` (6), beide im Deploy-Workflow und im Integritätsgate verankert.
- Der Vinted-Browser-Worker wird vom selben Deploy-Workflow ausgeliefert; die Größenextraktion ist damit Teil desselben Releases.
- Produktionsabnahme: gemeinsam mit 1.7.1 auf Commit `5f7ed1d07b6fd92f2f76f73962f9dd31fb4c5893` erfolgt; 1.7.0 wurde nie einzeln ausgeliefert.

## 1.6.5 – 2026-08-12 – Aufräumen und eine Quelle für die Release-Identität

- 94 Python-Module entfernt, die von keinem Einstiegspunkt mehr erreichbar waren (7.988 Zeilen), samt der 30 Testdateien, die ausschließlich sie geprüft haben.
- Erreichbarkeit über den Import-Graph ab den echten Einstiegspunkten bestimmt, einschließlich der dynamisch per `importlib` geladenen Suchmodule; Paket-Initialisierer und Konsolen-Entrypoints blieben ausgenommen.
- 129 Browser-Assets entfernt, die von keiner Seite und keinem Service-Worker-Precache mehr geladen wurden; `cloudflare/public` schrumpft auf die 33 tatsächlich ausgelieferten Dateien.
- Verwaisten `cloudflare_worker.py` im Repo-Wurzelverzeichnis gelöscht: er zeigte auf den 0.3-Stand, während produktiv `src/generic_parser/cloudflare_worker.py` läuft.
- 19 `RELEASE_NOTES_*.md` aus dem Wurzelverzeichnis entfernt; die Inhalte stehen unverändert in `CHANGELOG.md` und `docs/releases/`.
- Zehn versionsgebundene Einmal-Workflows entfernt; es bleiben Deploy, Publish, das PR-Integritätsgate und der Vinted-PoC.
- `scripts/sync_release_identity.py` ergänzt: `release_identity.py` ist die einzige Quelle, zwölf abgeleitete Artefakte werden erzeugt statt gepflegt. Der Deploy-Workflow prüft die Konsistenz mit `--check` und bricht bei Abweichung ab.
- Versionsgebundene Assertions aus den Gate-Tests entfernt; sie leiten Version, Build-ID und Asset-Kennung jetzt aus der Quelle ab.
- Fehler nebenbei behoben: die Asset-Query-Strings der drei HTML-Seiten hingen noch auf `gp-163`, obwohl 1.6.4 ausgeliefert war.
- Suchkern, Paginierung, Marktplatzadapter, Klassifizierung, Scoring, Modul-v1, Modul-v2, Fortsetzungstoken und Browseroberfläche sind unverändert.
- Produktionsabnahme: ausstehend. Rollback-Ziel unverändert: 1.6.2 / `gp-162-20260810-1`.

## 1.6.4 – 2026-08-12 – Reiner Versionsbump zur Verifikation der Release-Kette

- Release-Identität von `1.6.3` / `gp-163-20260810-1` auf `1.6.4` / `gp-164-20260812-1` gehoben.
- Keine funktionalen Änderungen: Suchkern, Marktplatzadapter, Klassifizierung, Scoring, Modul-v1, Modul-v2, Fortsetzungstoken und Browseroberfläche sind gegenüber 1.6.3 unverändert.
- Zweck dieses Releases ist ausschließlich die Verifikation, dass Build, Deployment und die Auslieferung einer neuen Version bis auf das Endgerät im Browser durchlaufen.
- Service-Worker-Cache auf `generic-parser-mobile-gp-164` umgestellt, damit Endgeräte die neue Version nicht aus dem alten Asset-Cache bedienen.
- Produktionsabnahme: ausstehend. Rollback-Ziel unverändert: 1.6.2 / `gp-162-20260810-1`.

## 1.6.3 – 2026-08-10 – Mobile Transporterholung bei langen Suchläufen

- Safari-Fehler `Load failed` aus dem Hauptsuchpfad als wiederholbare Transportunterbrechung klassifiziert, statt den Lauf nach dem ersten verlorenen API-v2-Paket zu beenden.
- Dasselbe unveränderte Paket mit demselben Fortsetzungstoken bis zu sechs Mal kurz gestaffelt erneut senden lassen; erfolgreiche Pakete behalten `0 ms` Pause auf dem Paid Worker.
- Vinted-Hintergrunddetails während der primären Paketfolge zurückgestellt, damit Mobilgeräte nicht gleichzeitig Hauptsuche und Detailstrom transportieren müssen.
- Fortsetzen auf derselben geöffneten Seite verwendet zuerst den vollständigen Arbeitsspeicherstand und behält dadurch auch flüchtige eBay-Treffer. Die weiterhin verbotene eBay-Suchergebnispersistenz bleibt unverändert.
- Fehlermeldungen unterscheiden nun wahrheitsgemäß zwischen Treffern, die auf der geöffneten Seite erhalten bleiben, und den dauerhaft gespeicherten Nicht-eBay-Treffern samt Fortsetzungspunkt.
- Quellenzähler zählen eindeutige `listing_key`-Werte statt rohe, möglicherweise wiederholte Zeilen; Vinted-Detailstatus verwendet durchgehend `vollständig / insgesamt`.
- Neuen ausführbaren Regressionstest ergänzt: 30 Pakete, einmaliger Safari-Abbruch auf Paket 29, automatische Fortsetzung mit 819 unveränderten In-Memory-Treffern.
- Modul-v1, API-v2-Schema und Tokenbindung, Marketplace-Adapter, Klassifizierung, Favoriten und das freundliche 1.6-Farbschema bleiben kompatibel.
- Produktionsabnahme: ausstehend. Rollback-Ziel: 1.6.2 / `gp-162-20260810-1`.

## 1.6.2 – 2026-08-10 – Robuster Browserstart und neue Log-Oberfläche

- Den Safari-Fehler behoben, bei dem ein einzelnes `Load failed` der Release-Identität die Websuche dauerhaft als „Live-Suche gesperrt“ blockierte.
- Minimale Release-Identität in das Browser-Asset eingebettet und die Live-Prüfung mit kurzen Wiederholungen in den Hintergrund verschoben; Diagnosefehler blockieren keine API-v2-Suche mehr.
- Optional nachgeladenen Controller bei wiederholtem Abruffehler in einen direkten, funktionsfähigen API-v2-Modus zurückfallen lassen.
- Service Worker so korrigiert, dass `/health`, `/version`, `/diagnostics`, `/search` und sämtliche `/api/`-Pfade niemals als statische Assets behandelt werden und HTML nie als JSON-/JavaScript-Ersatz zurückgegeben wird.
- `Log & Diagnose` auf das freundliche 1.6-Farbschema und ein kompaktes mobiles Layout umgestellt; Ereignisse sind einklappbar und nach Problemen, Suchläufen oder Quellen filterbar.
- In der Diagnose „Websuche: API v2“ klar von „Kompatibilität: API v1“ getrennt.
- Suchkern, API-v1/v2-Verträge, Quellenadapter, Klassifizierung, Favoriten, Stopp/Fortsetzen und Paid-Worker-Timing unverändert beibehalten.
- Produktionsabnahme erfolgreich: Workflow `31423346170` bestätigte auf Commit `9e2a09b71c6d6cea7bca4e13b0ecd2a515758907` Identität, API v2, alle drei Marktplätze, eBay-Verträge und Vinted-Detailanreicherung. Der direkte Browserlauf `Zelda` lud 378 eindeutige eBay-Treffer bis zum kontrollierten, korrekt fortsetzbaren Stopp; Startseite und neue Log-Oberfläche meldeten 1.6.2, und acht aktive Browserassets waren bytegenau zum geprüften Commit.
- Rollback-Ziel: 1.6.1 / `gp-161-20260810-1`.

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
