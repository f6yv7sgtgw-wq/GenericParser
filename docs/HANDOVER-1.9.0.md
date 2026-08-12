# Übergabe an die nächste Sitzung — Stand nach 1.8.9

Diese Datei fasst zusammen, was belegt ist, was offen ist und wie es weitergehen
sollte. Sie ist so geschrieben, dass eine Sitzung ohne Vorgeschichte damit
arbeiten kann.

## 1. Stand

- **Produktiv: 1.8.9** / `gp-189-20260812-1`, abgenommen. Rollback-Ziel 1.8.8.
- 314 Python-Tests und 55 JS-Tests grün; beide CI-Workflows fahren die
  **vollständige** Suite, keine Whitelist mehr.
- Live: https://genericparser.f6yv7sgtgw.workers.dev

### Arbeitsumgebung

Auf dem Rechner gibt es **kein** `pip` und kein systemweites `pytest`. Die
Testumgebung liegt unter `.venv` (mit `python3 -m venv` erstellt, `python3-venv`
ist installiert). Tests laufen mit `.venv/bin/pytest -q`.

Node ist **v18**. Zwei Tests in `pocs/ebay-notifications/test/` brauchen globales
Web Crypto und schlagen lokal fehl; unter CI-Node 22 sind sie grün. Lokal mit
`node --experimental-global-webcrypto` prüfbar. **Das ist kein Fehler im Code.**

### Release-Ablauf (wird strikt so gehandhabt)

1. `src/generic_parser/release_identity.py` ist die **einzige** Quelle für
   Version und Build-ID. Danach `python3 scripts/sync_release_identity.py`
   ausführen — es schreibt zwölf abgeleitete Artefakte.
2. `VERSION.json` inhaltlich pflegen: `purpose`, `status`, `verification`-Keys,
   `metadata_schema` hochzählen, `rollback_plan` auf die zuletzt **abgenommene**
   Version setzen.
3. Eintrag in `CHANGELOG.md`, Zeile in `docs/RELEASE_INDEX.md`, Status in
   `ROADMAP.md`, bei größeren Releases eine Notiz unter `docs/releases/`.
4. Branch `agent/genericparser-<version>`, PR, Checks abwarten, squash-mergen.
   Der Merge nach `main` löst den Deploy aus.
5. Nach der Bestätigung des Nutzers die Abnahme nachtragen: `status: stable`,
   `production_acceptance: passed`, `production_commit`, `production_workflow_run`,
   `accepted_at`.

Die git-Identität ist bewusst ein Pseudonym (`f6yv7sgtgw-wq`). **Niemals** den
Klarnamen oder eine Firmen-E-Mail als Autor eintragen.

## 2. Belegte Befunde aus dem Eventlog

Ein vollständiger Lauf mit `super mario kart 8` (1291 Treffer, 64 Pakete, keine
Retries) hat die lange offenen Fragen entschieden:

| Quelle | Pakete | Treffer | Status | Grund |
|---|---|---|---|---|
| eBay | 39 | 975 | `ok` | `batch_complete` — natürliches Ende |
| Kleinanzeigen | 14 | 91 | `ok` | `packet_budget_reached` — **abgeschnitten** |
| Vinted | 11 | 250 | **`blocked`** | `vinted_session_bootstrap_access_limit` |

Zwei frühere Vermutungen waren damit **falsch**: Kleinanzeigen endet nicht
natürlich, sondern läuft ins Paketbudget; Vinted wird tatsächlich blockiert.
Nur eBay endet regulär.

Schrittweiten sind je Quelle verschieden und so gebaut: Kleinanzeigen 7
(`packet_size: 7`, seit 1.0.0 zugesagt), Vinted 25 (`MAX_RESULTS`), eBay 25
(`PAGE_SIZE`). Die Quellen rotieren seit 1.8.5 paketweise.

## 3. Das eigentliche Thema für 1.9.0: Relevanzprüfung

### Problem

`super mario kart 8` liefert 1291 Treffer, davon 975 von eBay. Die
Marktplatzsuchen arbeiten mit ODER-Semantik über die Wörter: „super", „mario",
„kart", „8" trifft jedes Mario-Spiel, jeden Kart-Artikel und alles mit einer 8.

Der bestehende Klassifizierer (`product_classification.py`) entscheidet die
**Produktart** — Hauptprodukt, Zubehör, Konvolut, Gesuch — und die Ampelfarbe.
Er beantwortet **nicht**, ob der Titel zur Suchanfrage passt. Genau dafür gäbe es
die Pflichtbegriffe im Suchkriterien-Panel, aber die sind standardmäßig leer, und
niemand pflegt sie von Hand.

### Vorschlag

Eine **quellenneutrale Relevanzprüfung**, die aus der Anfrage selbst abgeleitet
wird und im selben Muster arbeitet wie `normalize_condition`: eine Funktion, eine
Fallsammlung, ein additives Feld.

**Wo:** neues Modul `src/generic_parser/relevance.py`, aufgerufen in
`search_service_v0450._decorate_listing`, direkt neben der Klassifizierung. Damit
gilt es für alle drei Quellen gleich und wirkt auch auf abgeleitete
Konvolut-Kacheln, die dort ohnehin erneut dekoriert werden.

**Wie:**

1. Anfrage in Begriffe zerlegen, normalisiert über `normalize_text` aus
   `normalization.py` (Umlaute, Interpunktion, Groß-/Kleinschreibung).
2. Begriffe gewichten. **Tragende** Begriffe sind Substantive und Zahlen
   (`mario`, `kart`, `8`); Füllwörter (`super`, `neu`, `original`, `set`) dürfen
   allein keinen Treffer rechtfertigen. Eine kleine Stoppwortliste reicht.
3. Deckung im Titel messen: Anteil der tragenden Begriffe, die vorkommen.
   Der Beschreibungstext zählt schwächer, weil er bei Konvoluten alles Mögliche
   nennt.
4. Schreibvarianten berücksichtigen — **hier liegt das Risiko**. „Mario Kart 8
   Deluxe" muss passen, „MK8" sollte passen, „Mario Party 8" darf nicht passen.
   Zahlen sind heikel: „8" darf nicht auf „Mario Kart 8 Deluxe **Set von 8**"
   verallgemeinern und nicht auf „Mario Kart" ohne Zahl.
5. Ergebnis additiv ausgeben: `relevance` mit `score` (0..1), `matched_terms`,
   `missing_terms` — analog zu `classification`. Bestehende v2-Bedeutungen
   bleiben unberührt.
6. Ampel: unter einer Schwelle auf Rot, im Graubereich auf Gelb (Prüffall).
   **Nicht hart filtern** — die Zusage „keine stille Kürzung" gilt. Der Nutzer
   sieht rote Treffer nur, wenn er den Statusfilter umstellt.

**Warum nicht hart filtern:** Genau diese Falle wurde in 1.7.0 beim Auktionsfilter
geschlossen (700 Treffer, Filter „Auktion" ergab null, weil Auktionen gar nicht
gesucht wurden). Ein Relevanzfilter, der Treffer verschwinden lässt, ohne es zu
sagen, wäre derselbe Fehler in neuer Form.

**Fixtures:** `tests/fixtures/normalization_cases.json` um einen Abschnitt
`relevance` erweitern — Anfrage, Titel, erwartete Einordnung. Kandidaten aus dem
echten Lauf: „Mario Kart 8 Deluxe Nintendo Switch" (passt), „Mario Party 8"
(passt nicht), „Nintendo Switch Konsole" (passt nicht), „MK8 Deluxe" (passt),
„Super Mario Odyssey" (passt nicht), „Mario Kart Wii" (passt nicht bei Anfrage
mit 8). Die Sammlung wird bereits von Python und dem Vinted-Worker gemeinsam
genutzt; dieser Abschnitt betrifft nur Python.

**Abnahmekriterium:** Derselbe Lauf `super mario kart 8` soll deutlich weniger
grüne Treffer zeigen, ohne dass ein tatsächliches „Mario Kart 8" auf Rot landet.
Vorher/Nachher lässt sich über die v2-API messen.

## 4. Weitere Verbesserungen der Suche

**Kleinanzeigen-Paketbudget.** Der Lauf endete mit `packet_budget_reached` nach
91 Treffern — es bleiben Treffer liegen, ohne dass es jemandem auffällt. Zu
klären: Wo das Budget gesetzt wird, ob es ein Schutz gegen Sperren ist, und ob es
angehoben oder pro Quelle unterschiedlich gefasst werden kann. Mindestens sollte
die Oberfläche sagen, dass hier gekürzt wurde.

**Vinted-Sitzungslimit — eingeplant für 1.9.1.** `vinted_session_bootstrap_access_limit`
im Browser-Worker (`pocs/vinted-browser/src/index.js`). Vinted begrenzt den
anonymen Katalogzugriff. Ein zweiter Lauf (`zelda link to the past`, direkt
nach dem Mario-Lauf) wurde schon nach 6 statt 11 Paketen blockiert — das
spricht für ein kumulatives Zeitfenster-Budget, nicht für eine Momentanrate.
Ein Zurück zur sequenziellen Suche hilft dann nicht (gleiche Gesamtzahl,
dichter gebündelt). Beschlossener Ansatz: **bewusster Abstand nur für Vinted**
innerhalb der Rotation — Vinted lässt seinen Zug aus, bis eine Abklingzeit
verstrichen ist, die übrigen Quellen rotieren pausenlos weiter. Vorher zu
klären: Fenstergröße aus mehreren Läufen mit Blockade-Zeitstempeln vermessen,
und ob ein erneuter Bootstrap nach Ablauf die Quelle wieder öffnet (dann
Wiederaufnahme statt endgültigem `blocked`).

**Ungleiche Schrittweiten.** Der Turnus liefert 7/25/25 pro Runde. Gleichziehen
beim Abruf ist teuer (Kleinanzeigen bräuchte drei bis vier Abrufe je Zug). Falls
die Mischung optisch stören sollte, wäre der richtige Hebel die **Anzeige** —
abwechselnd einsortieren statt in Ankunftsreihenfolge.

**Zustand und Versand sind bei zwei Quellen leer.** `condition_code` ist bei
Kleinanzeigen fast durchgehend `unknown`, `delivery.mode` bei Kleinanzeigen und
Vinted praktisch immer. Die Normalisierung ist korrekt — die Trefferlisten
liefern die Angaben schlicht nicht. Beide Filter sind damit für zwei von drei
Plattformen wirkungslos. Nachziehen ginge nur über Teaser-Parsing oder die
Detailseite.

## 5. Bekannte Issues und ihre Lösungswege

**Dynamisch geladene Assets.** Das 1.6.5-Aufräumen entfernte zwei Dateien, die
über zusammengebaute `fetch`-Pfade geladen werden: `auto-resume-04462.js` (die
automatische Wiederaufnahme war sechs Releases lang tot) und `controller-0411.js`
(dadurch scheiterte `loadControllerSource()`, und mit ihm die Abschaltung der
Latenzdrosselung — das war der Fünf-Sekunden-Timer). Beide sind in 1.8.9
wiederhergestellt, und `tests/test_release_189.py` prüft jeden per
`new URL('./…')` gebauten Pfad gegen das Dateisystem.
**Offen bleibt das Muster:** Es gibt weitere Loader, die Quelltext per `fetch`
holen, per Regex patchen und mit `Function(...)` ausführen. Schlägt ein
Ersetzungsmuster fehl, unterbleibt der gesamte `.then()`-Block **stillschweigend**.
Diese Konstruktion hat bereits zweimal zu unsichtbaren Ausfällen geführt. Sie
gehört durch etwas ersetzt, das laut scheitert — mindestens ein Log-Eintrag im
`catch`, besser ein Verzicht auf das Patchen zur Laufzeit.

**Stille Fehlschläge allgemein.** Beide Vorfälle blieben unentdeckt, weil das
Eventlog bis 1.8.8 **keinen Schreiber hatte** — alle Aufrufer prüften nur
`typeof window.gpEventLog === 'function'`. Seit 1.8.8 gibt es
`eventlog-writer-188.js`, seit 1.8.9 beschreibt das Log einen kompletten Lauf.
Beim Untersuchen eines Verdachts also **immer zuerst ein Log anfordern**.

**16 rote Tests aus der 0.4x-Ära** wurden repariert, nicht stillgelegt. Sie waren
jahrelang unsichtbar, weil die Workflows eine Whitelist fuhren. Assertions, die
den Lebenszyklus festschreiben (Version, Status, Rollback-Ziel), wurden durch
strukturelle Prüfungen ersetzt — beim nächsten Release nicht erneut hart pinnen.

**`scripts/check_deployment.py` wird nie ausgeführt**, nur kompiliert. Seine
Konstanten kommen inzwischen aus `VERSION.json` statt aus einem hart kodierten
`1.0.0`. Entweder in den Deploy-Workflow aufnehmen — dann prüft er die
Live-Identität wirklich — oder löschen.

**Konvolut-Budget.** Die Auflösung holt höchstens drei Detailseiten je
Ergebnisseite. Bei konvolutlastigen Suchen bleiben die übrigen unaufgelöst. Ein
Hintergrundpfad wie bei Vinted würde das heben.

**Deploy-Flakiness.** Ein Deploy scheiterte einmal am Pyodide-Download von GitHub
(`http2 error: refused stream`). Reine Netzwerkstörung, der Neustart lief durch.
Falls es sich häuft: Retry um den `pywrangler deploy`-Schritt.

## 5a. Befunde aus dem 1.9.0-Abnahmelauf (`lemmings snes`)

Die Relevanzprüfung ist abgenommen (249 Treffer, 97 Rot, sichtbare Grüne alle
echt, Grauzone korrekt Gelb). Drei Beobachtungen für die Nacharbeit:

- **Schreibvarianten sind der nächste Hebel (relevance-v2):** „SNES Lemminge
  Verpackt…" und „…Lemminge 2 Tribess…" sind echte Lemmings-Angebote, landeten
  aber auf Gelb, weil „lemminge"/„tribess" nicht exakt „lemmings" decken.
  Einfache Singular-/Plural- und Tippfehler-Toleranz (kleine Editierdistanz nur
  bei langen Begriffen) würde beide heben, ohne „Mario Party 8" wieder
  hereinzulassen.
- **Klassifizierer-Lücke „nur Anleitung":** „nur Spielanleitung", „NUR
  HANDBUCH", „Notice seule" (frz.) laufen als Hauptprodukt auf Grün durch —
  die `_ACCESSORY`-Liste kennt nur „anleitung einzeln"/„manual only".
- **Vinted-Kacheln verlieren die Relevanz-Begründung:** Nach der
  Hintergrund-Anreicherung mit Rescore zeigt „Warum?" bei Vinted nur noch
  „Suchbegriff teilweise erkannt", bei eBay dagegen beide Teile inklusive
  „(fehlt: …)". Die Farbe stimmt, nur die Begründung geht beim
  browserseitigen Rescore verloren — kosmetisch, aber inkonsistent.

## 6. Reihenfolge-Empfehlung

1. **Relevanzprüfung** (Abschnitt 3) — größter Nutzen für die Bedienbarkeit.
2. **Kleinanzeigen-Paketbudget** — stille Kürzung, betrifft die Vollständigkeit.
3. **Vinted-Sitzungslimit** — begrenzt eine ganze Quelle auf 250 Treffer.
4. **Laufzeit-Patching entschärfen** — verhindert die nächste unsichtbare Panne.
