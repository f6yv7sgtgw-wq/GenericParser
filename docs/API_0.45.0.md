# GenericParser API 0.45.0

Vollständige, versionsgebundene API- und Funktionsdokumentation für den Modulvertrag `generic-parser-module-v1`.

| Merkmal | Wert |
|---|---|
| Produktversion | `0.45.0` |
| Build-ID | `gp-0450-20260805-1` |
| Modul- und API-Vertrag | `generic-parser-module-v1` |
| Fachlicher Suchkern | `0.44.4` |
| Operative Rückfallreferenz | `0.44.6.5` |
| Laufzeitreferenz | `0.44.6.2` |
| Quelle | ausschließlich Kleinanzeigen |
| Zielplattform | Cloudflare Python Workers, Free-Tarif berücksichtigt |
| Stand der Plattformgrenzen | 2026-08-05 |

Diese Datei ist der unveränderliche API-Snapshot für Release 0.45.0. Die jeweils aktuelle Dokumentation eines späteren Releases erhält eine eigene Datei.

## 1. Zweck und Verantwortungsgrenze

GenericParser übersetzt Suchprofile aus Evercade, SNES-PAL oder weiteren Projekten in eine Kleinanzeigen-Suche und liefert ein einheitliches Ergebnisformat zurück. Das Modul übernimmt:

- Erzeugung der Kleinanzeigen-Suchadresse,
- seiten- und paketweisen Abruf,
- Extraktion von Anzeigenkarten,
- Normalisierung von Titel, URL, Bild, Preis und Ort,
- Bewertung der aktiv gesetzten Regeln,
- Ampelklassifizierung,
- technische Pagination und Diagnose.

Das aufrufende Projekt bleibt verantwortlich für:

- Produktkatalog und Sammlungsstatus,
- fachliche Entscheidung, welches Produkt gesucht wird,
- persistente Deduplizierung über mehrere Antworten,
- Anzeige, Benachrichtigung und Kaufentscheidung,
- Wiederholungsstrategie und Abbruch,
- Schutz und Verteilung eines optionalen Zugriffstokens.

0.45.0 ist kein serverseitiger Hintergrunddienst. Eine vollständige Mehrseiten-Suche wird vom Browser oder vom aufrufenden Projekt über mehrere HTTP-Anfragen koordiniert.

## 2. Basis-URL, Formate und Versionserkennung

Alle Pfade sind relativ zur bereitgestellten Worker-URL, beispielsweise:

```text
https://<worker>.<account>.workers.dev/api/module/v1/capabilities
```

JSON-Anfragen verwenden `Content-Type: application/json`. JSON-Antworten verwenden `application/json`. Interaktive Swagger- und ReDoc-Seiten sind deaktiviert; die von FastAPI erzeugte Maschinenspezifikation ist unter `GET /openapi.json` verfügbar.

Jede durch GenericParser erzeugte JSON-Antwort enthält diese Header. Framework-Antworten,
die vor der GenericParser-Verarbeitung entstehen – insbesondere FastAPI-Validierungsfehler
mit HTTP 422 und `/openapi.json` – sind davon ausgenommen:

| Header | Wert in 0.45.0 |
|---|---|
| `X-GenericParser-Version` | `0.45.0` |
| `X-GenericParser-Build` | `gp-0450-20260805-1` |
| `X-GenericParser-Contract` | `generic-parser-module-v1` |
| `X-GenericParser-Module-Contract` | `generic-parser-module-v1` |
| `Cache-Control` | `no-store` |

Integrationen müssen mindestens `contract`, Versionsheader und Build-ID protokollieren. Ein unbekannter Vertragsname darf nicht stillschweigend als kompatibel behandelt werden.

## 3. Zugriffsschutz

Der Worker kann optional mit dem Secret `APP_TOKEN` geschützt werden. Ist das Secret gesetzt, benötigen die beiden Suchendpunkte folgenden Header:

```http
X-GenericParser-Token: <token>
```

Das gilt für:

- `POST /api/module/v1/search`
- `POST /api/search`

Health-, Versions-, Capabilities-, Profilvalidierungs-, OpenAPI- und Selbsttest-Endpunkte sind in 0.45.0 nicht durch `APP_TOKEN` geschützt. Wer diese Informationen nicht öffentlich bereitstellen will, muss den Worker zusätzlich über Cloudflare Access oder eine vorgeschaltete Zugriffskontrolle absichern.

Das Token darf nicht in Debug-Payloads, URLs oder Eventlogs geschrieben werden. Die PWA speichert ein eingegebenes Token nur lokal im Browser.

## 4. Endpunktübersicht

| Methode | Pfad | Netzwerk zu Kleinanzeigen | Zweck |
|---|---|---:|---|
| `GET` | `/health` | nein | Laufzeit- und Versionsstatus |
| `GET` | `/api/version` | nein | identisch zu `/health` |
| `GET` | `/openapi.json` | nein | maschinenlesbares OpenAPI-Schema |
| `GET` | `/api/module/v1/capabilities` | nein | Fähigkeiten und Referenzstände |
| `POST` | `/api/module/v1/profile/validate` | nein | Profil und Legacy-Übersetzung validieren |
| `POST` | `/api/module/v1/search` | ja | ein Arbeitspaket mit höchstens sieben Karten suchen |
| `GET` | `/api/module/v1/self-test` | nein | opt-in Vertrags- und Adaptertest |
| `POST` | `/api/search` | ja | kompatibler PWA-/Legacy-Vertrag aus 0.44.6.5 |

## 5. `GET /health` und `GET /api/version`

Beide Pfade liefern dieselbe Antwort. Der Aufruf lädt den Suchservice nicht aktiv und ruft Kleinanzeigen nicht auf.

Wichtige Antwortfelder:

| Feld | Bedeutung |
|---|---|
| `status` | bei erfolgreicher Laufzeit `ok` |
| `version`, `build_id` | laufende Produkt- und Build-Identität |
| `api_contract`, `module_contract` | aktiver Vertrag |
| `search_ready` | statische Bereitschaftsaussage des Bootstraps |
| `service_loaded` | ob der Suchservice in diesem Isolat bereits importiert wurde |
| `packet_size` | höchstens sieben ausgewählte Karten je Anfrage |
| `pause_ms` | empfohlene Browserpause zwischen Arbeitspaketen: 5.000 ms |
| `pagination_strategy` | Navigation über den echten `Weiter`-Link der Quellseite |
| `functional_reference` | fachlicher Kern 0.44.4 |
| `operational_reference` | Rückfallstand 0.44.6.5 |
| `runtime_reference` | Laufzeitverhalten 0.44.6.2 |
| `debug_logging` | Debug standardmäßig aus; Aktivierungswege |
| `contract_tests` | Selbsttests standardmäßig aus und ohne Kleinanzeigen-Abruf |
| `controller_recovery` | einmalige Browser-Recovery aus der Referenzlinie |
| `last_import_error` | letzter Importfehler innerhalb desselben Isolats oder `null` |

`search_ready: true` ersetzt keinen echten Suchtest. Es bestätigt nur, dass der aktive Bootstrap diesen Suchpfad anbietet.

## 6. `GET /api/module/v1/capabilities`

Der Endpunkt liefert die vertraglich angebotenen Fähigkeiten:

```json
{
  "contract": "generic-parser-module-v1",
  "sources": ["kleinanzeigen"],
  "integrations": ["evercade", "snes-pal"],
  "pagination": "one-work-packet-per-request",
  "packet_size": 7,
  "debug_default": false,
  "tests_default": false,
  "legacy_reference": "0.44.6.5",
  "functional_reference": "0.44.4",
  "deployment": {}
}
```

Die Liste `integrations` bezeichnet mitgelieferte Profiladapter, nicht bereits angebundene oder deployte Fremdprojekte.

## 7. Suchprofil `ModuleSearchProfile`

`POST /api/module/v1/profile/validate` erwartet direkt ein Suchprofil. `POST /api/module/v1/search` erwartet es im Feld `profile`.

| Feld | Typ | Standard | Regeln und Wirkung |
|---|---|---|---|
| `profile_id` | String | `manual` | stabile ID des aufrufenden Projekts; wird unverändert zurückgegeben |
| `display_name` | String | `Manuelle Suche` | nur beschreibend; beeinflusst die Suche nicht |
| `query` | String | – | erforderlich; effektiv 2 bis 120 Zeichen |
| `required_terms` | String-Liste | `[]` | alle gesetzten Begriffe müssen erkannt werden; leere und doppelte Werte werden entfernt |
| `excluded_terms` | String-Liste | `[]` | erkannte Begriffe führen zu einer Ablehnung |
| `model_patterns` | String-Liste | `[]` | optionale Modell-/Schreibvarianten; fehlende Erkennung erzeugt einen Prüffall |
| `brands` | String-Liste | `[]` | optionale Marken; fehlende Erkennung erzeugt einen Prüffall |
| `max_price` | Zahl oder `null` | `null` | muss größer als 0 sein; Überschreitung ist eine harte Ablehnung |
| `market_value` | Zahl oder `null` | `null` | muss größer als 0 sein; bis 20 % darüber gelb, darüber rot |
| `postal_code` | String oder `null` | `null` | exakt fünf deutsche Ziffern; nur zusammen mit `location_id` |
| `location_id` | positive Ganzzahl oder `null` | `null` | verifizierte Kleinanzeigen-Location-ID |
| `radius_km` | Ganzzahl oder `null` | `null` | 0 bis 200; erfordert `location_id` |
| `accept_bundles` | Boolean | `false` | bei `false` ist ein erkanntes Bundle eine harte Ablehnung |
| `accept_incomplete` | Boolean | `false` | bei `false` ist erkannter Defekt/Unvollständigkeit eine harte Ablehnung |
| `include_review` | Boolean | `true` | Prüffälle im Ergebnis belassen |
| `include_rejected` | Boolean | `true` | abgelehnte Treffer im Ergebnis belassen |
| `sort_by` | Enum | `relevance` | `relevance`, `date`, `price_asc` oder `price_desc` |

Listenfelder akzeptieren in der Python-Schnittstelle auch einen kommaseparierten String. Für HTTP-Clients wird eine JSON-Liste empfohlen.

Leere optionale Felder werden vor der Übergabe an den Referenzkern entfernt. Ein leeres Feld ist damit keine aktive Regel. Die Boolean-Felder werden immer übertragen, weil `false` bei Bundle- und Unvollständigkeitsprüfung eine aktive Ausschlussregel ist.

Lokale Suche:

- `postal_code` ohne `location_id` ist ungültig.
- `radius_km` ohne `location_id` ist ungültig.
- Die API ermittelt in 0.45.0 keine Location-ID. Das aufrufende Projekt muss sie vorher verifizieren und speichern.

## 8. `POST /api/module/v1/profile/validate`

Beispiel:

```bash
curl -sS -X POST "$BASE_URL/api/module/v1/profile/validate" \
  -H 'Content-Type: application/json' \
  --data '{
    "profile_id": "evercade:interplay-1",
    "display_name": "Evercade · Interplay Collection 1",
    "query": "Evercade Interplay Collection 1",
    "required_terms": [],
    "brands": ["Evercade", "Blaze"],
    "max_price": 35,
    "market_value": 30
  }'
```

Erfolgsantwort:

```json
{
  "contract": "generic-parser-module-v1",
  "valid": true,
  "profile": {},
  "legacy_payload": {},
  "empty_fields_ignored": true,
  "reference_request_validated": true
}
```

`profile` ist das normalisierte Modulprofil. `legacy_payload` zeigt exakt, was an den 0.44.4-Requestvertrag übergeben würde. Der Endpunkt führt keine Suche aus.

## 9. Suchrequest `ModulePageRequest`

| Feld | Typ | Standard | Bedeutung |
|---|---|---|---|
| `profile` | `ModuleSearchProfile` | – | erforderlich |
| `page` | Ganzzahl | `0` | virtuelle Arbeitspaketnummer 0 bis 499 |
| `source` | String | `auto` | in 0.45.0 ist nur `auto` vertraglich unterstützt |
| `debug` | `ModuleDebugOptions` | Debug aus | optionale Antwortdiagnose |

Debugoptionen:

| Feld | Typ | Standard | Bedeutung |
|---|---|---|---|
| `enabled` | Boolean | `false` | Debugbericht in der Antwort aktivieren |
| `include_payload` | Boolean | `false` | übersetztes Legacy-Payload in die Antwort aufnehmen |
| `include_timings` | Boolean | `true` | relative Zeitmarken an Debugereignisse anhängen |
| `max_events` | Ganzzahl | `50` | 1 bis 200 Ereignisse |

Alternativ aktiviert `X-GenericParser-Debug: 1` den Debugbericht. Der Header überschreibt kein explizit aktiviertes Payloadlogging; `include_payload` bleibt standardmäßig `false`.

## 10. `POST /api/module/v1/search`

Beispiel:

```bash
curl -sS -X POST "$BASE_URL/api/module/v1/search" \
  -H 'Content-Type: application/json' \
  -H "X-GenericParser-Token: $APP_TOKEN" \
  --data '{
    "profile": {
      "profile_id": "snes-pal:super-metroid",
      "display_name": "SNES PAL · Super Metroid",
      "query": "SNES Super Metroid",
      "required_terms": ["PAL"],
      "excluded_terms": ["NTSC", "Repro", "Reproduction"],
      "brands": ["Nintendo"],
      "market_value": 70,
      "include_review": true,
      "include_rejected": true
    },
    "page": 0,
    "source": "auto",
    "debug": {"enabled": false}
  }'
```

Eine erfolgreiche Anfrage verarbeitet genau ein Arbeitspaket. Sie ist keine vollständige Suche.

### 10.1 Virtuelle Pagination

Eine Kleinanzeigen-Quellseite enthält typischerweise bis zu 25 Anzeigenkarten. GenericParser teilt sie in bis zu vier virtuelle Pakete:

| virtuelle `page` | Quellseite | Paketindex | Kartenbereich |
|---:|---:|---:|---|
| 0 | 0 | 0 | 1–7 |
| 1 | 0 | 1 | 8–14 |
| 2 | 0 | 2 | 15–21 |
| 3 | 0 | 3 | 22–25 |
| 4 | nächste Quellseite | 0 | 1–7 |

Der Client ruft `pagination.next_page` erst nach der empfohlenen Pause von 5 Sekunden auf. Er beendet die Suche, wenn `pagination.complete` wahr oder `next_page` nicht vorhanden ist.

Die Quellseite kann für aufeinanderfolgende Pakete erneut geladen werden. Anzeigen können sich zwischen diesen Abrufen ändern. Deshalb muss das aufrufende Projekt über die Anzeigen-ID global deduplizieren.

### 10.2 Antwort `ModulePageResponse`

```json
{
  "contract": "generic-parser-module-v1",
  "profile_id": "snes-pal:super-metroid",
  "listings": [],
  "pagination": {
    "current_page": 0,
    "next_page": 1,
    "complete": false,
    "source": "html-light-packets",
    "stop_reason": "work_packet_complete"
  },
  "summary": {
    "fetched": 7,
    "visible": 7,
    "hidden": 0,
    "unique": 7,
    "reported_total": 63,
    "traffic_lights": {"green": 1, "yellow": 3, "red": 3}
  },
  "deployment": {},
  "debug": null
}
```

Felder mit `null` werden bei der HTTP-Antwort des Modulendpunkts ausgelassen.

### 10.3 Listing-Felder

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | String | Kleinanzeigen-Anzeigen-ID; Deduplizierungsschlüssel |
| `title` | String | extrahierter Titel |
| `url` | String | absolute Anzeigen-URL |
| `image_url` | String, optional | extrahierte Bild-URL |
| `price` | Zahl, optional | normalisierter Preis; Versand wird nicht addiert |
| `price_raw` | String, optional | Originaldarstellung des Preises |
| `postal_code` | String, optional | aus der Karte extrahierte PLZ |
| `place` | String, optional | aus der Karte extrahierter Ort |
| `source` | String | in 0.45.0 `kleinanzeigen` |
| `match` | Objekt | Entscheidung, Score und Begründung |
| `traffic_light` | Objekt | aktive Einzelkriterien und Gesamtampel |
| `result_info` | Objekt | erkannter Angebotstyp, Zustand, Umfang und Passung |

Nicht garantiert sind Detailseitenbeschreibung, Versandkosten, Verkäuferdaten, rechtssichere Zustandsangabe oder Verfügbarkeit nach dem Suchzeitpunkt.

### 10.4 Pagination-Felder

| Feld | Bedeutung |
|---|---|
| `current_page` | angeforderte virtuelle Paketnummer |
| `next_page` | nächste Paketnummer oder nicht vorhanden |
| `complete` | natürliches Ende nach aktueller Quellinformation erkannt |
| `source` | tatsächlich verwendeter technischer Quellpfad |
| `stop_reason` | technischer Grund, beispielsweise `work_packet_complete`, `empty_page_verified` oder `next_link_missing` |

### 10.5 Summary-Invarianten

Für jede erfolgreiche Paketantwort gilt:

```text
fetched = visible + hidden
visible = Anzahl der Elemente in listings
unique = paketbezogene Zahl, nicht globaler Suchstand
```

`reported_total` ist ausschließlich diagnostisch. Es darf weder als Vollständigkeitsgarantie noch allein als Abbruchbedingung verwendet werden.

## 11. Bewertungs- und Ampellogik

Nur gesetzte optionale Regeln werden bewertet. Der Suchbegriff selbst ist immer aktiv.

### 11.1 Suchbegriff

Stoppwörter werden entfernt und die verbleibenden Suchbegriffe mit Titeltokens verglichen:

- mindestens 75 % erkannt: grün,
- mindestens 40 % erkannt: gelb,
- darunter: harte rote Ablehnung.

### 11.2 Pflicht- und Ausschlussbegriffe

Bei der leichten Kartenextraktion werden Titel und vorhandener Kartentext verwendet. Die abschließende 0.44.4-Ampel bewertet diese Regeln anhand des Titels. Dadurch kann die sichtbare Ampelbegründung strenger sein als die erste Extraktionsentscheidung.

- fehlender Pflichtbegriff: harte rote Ablehnung,
- erkannter Ausschlussbegriff: harte rote Ablehnung,
- leere Listen: keine aktive Regel.

### 11.3 Modell und Marke

Eine erkannte Variante beziehungsweise Marke ist grün. Fehlt die Erkennung, wird das Kriterium gelb; allein daraus entsteht keine harte Ablehnung.

### 11.4 Angebotstyp, Zustand und Umfang

Die Klassifikation arbeitet heuristisch auf Titelbasis:

- Gesuch statt Verkaufsangebot: harte rote Ablehnung,
- erkannter Defekt oder Unvollständigkeit bei `accept_incomplete: false`: harte rote Ablehnung,
- erkanntes Bundle bei `accept_bundles: false`: harte rote Ablehnung.

Die Erkennung ist keine semantische Detailseitenanalyse und kann Formulierungen übersehen oder falsch einordnen.

### 11.5 Preise

- `max_price`: fehlender/VB-Preis gelb, bis einschließlich Grenze grün, darüber harte rote Ablehnung.
- `market_value`: fehlender/VB-Preis gelb, bis Richtwert grün, bis 20 % darüber gelb, darüber rot.
- Versandkosten werden in 0.45.0 nicht zuverlässig extrahiert und nicht zum Preis addiert.

### 11.6 Gesamtentscheidung

- mindestens ein hart rotes Kriterium oder mindestens zwei rote Kriterien: `reject`, rot, Score 0,
- mindestens ein sonstiges rotes oder gelbes Kriterium: `review`, gelb, Score 60,
- sonst: `accept`, grün, Score 100.

`include_review` und `include_rejected` bestimmen, welche Kategorien in `listings` sichtbar bleiben. Sie ändern nicht die Bewertung.

## 12. Debugmodus

Debug ist standardmäßig vollständig aus. Bei Aktivierung entstehen zwei getrennte Diagnoseebenen:

1. Der Modulendpunkt liefert einen begrenzten `debug`-Block mit Trace-ID, Laufzeit und Phasenereignissen.
2. Die PWA protokolliert Status, Dauer und den empfangenen Debugbericht lokal im Browser-Eventlog.

Es handelt sich nicht um eine dauerhafte serverseitige Logdatenbank. Browserlogs liegen in `localStorage` des jeweiligen Geräts. Cloudflare-Plattformlogs unterliegen zusätzlich den Kontoeinstellungen und Plattformgrenzen.

`include_payload: true` kann Suchbegriffe, Preise und Ortsparameter in der API-Antwort wiedergeben. Diese Option ist nur für gezielte Diagnose vorgesehen.

## 13. `GET /api/module/v1/self-test`

Ohne Aktivierung:

```http
GET /api/module/v1/self-test
```

Antwort: HTTP 409, `tests_enabled: false`, `network_used: false`.

Aktivierung:

```http
GET /api/module/v1/self-test?enabled=true
```

oder:

```http
X-GenericParser-Tests: 1
```

Der Test prüft Profilnormalisierung, leere Felder, Pagination-Mapping, Ergebnisvertrag, Ampelzusammenfassung sowie Evercade- und SNES-Adapter. Er ruft Kleinanzeigen nicht auf und verändert keinen Suchstand.

## 14. Projektadapter

### 14.1 Evercade

```python
from generic_parser import evercade_profile

profile = evercade_profile(
    "Interplay Collection 1",
    profile_id="evercade:red-04",
    variants=["Interplay 1", "Interplay Collection I"],
    max_price=35,
    market_value=30,
    excluded_terms=["nur Hülle"],
    accept_bundles=False,
    accept_incomplete=False,
)
```

Der Adapter setzt:

| Eingabe | Modulprofil |
|---|---|
| Cartridge-Name | `query = "Evercade <Name>"` |
| Varianten | `model_patterns` |
| feste Marken | `brands = ["Evercade", "Blaze"]` |
| Preiswerte | `max_price`, `market_value` |
| Projekt-ID | explizite ID oder abgeleitetes `evercade:<slug>` |

Der Adapter kennt weder vorhandene Cartridges noch Kaufstatus, Gesamtpreis inklusive Versand oder Händlervertrauen.

### 14.2 SNES-PAL

```python
from generic_parser import snes_pal_profile

profile = snes_pal_profile(
    "Super Metroid",
    profile_id="snes-pal:super-metroid",
    variants=["SuperMetroid"],
    max_price=80,
    market_value=70,
)
```

Der Adapter setzt:

| Eingabe | Modulprofil |
|---|---|
| Titel | `query = "SNES <Titel>"` |
| PAL-Schutz | `required_terms = ["PAL"]` |
| Standardausschlüsse | `NTSC`, `Repro`, `Reproduction` |
| Varianten | `model_patterns` |
| feste Marke | `brands = ["Nintendo"]` |
| Projekt-ID | explizite ID oder abgeleitetes `snes-pal:<slug>` |

Der Titel einer echten PAL-Anzeige enthält nicht zwingend das Wort `PAL`. Das Standardprofil ist deshalb bewusst streng und kann gültige Angebote als rot markieren. Das SNES-Projekt muss entscheiden, ob es diese Regel beibehält, lockert oder durch eigene Katalogmerkmale ergänzt.

## 15. Empfohlener Clientablauf für Evercade und SNES

1. `GET /api/version` und Vertragsname prüfen.
2. Suchprofil lokal erzeugen.
3. Profil einmal über `/profile/validate` prüfen.
4. `/search` mit `page: 0` aufrufen.
5. Listings anhand `id` in den projektspezifischen Suchstand übernehmen.
6. Antwortinvarianten prüfen.
7. Mindestens 5 Sekunden warten.
8. Mit `next_page` fortsetzen, solange `complete` falsch ist.
9. Bei Fehlern den letzten bestätigten Stand behalten; keine Seite als erfolgreich markieren.
10. Nach Abschluss Ergebnisse fachlich im Projekt auswerten.

Mehrere Projekte sollten nicht unkoordiniert parallel denselben Free-Worker belasten. Ein gemeinsames Anfragebudget und eine zentrale Zeitplanung sind empfehlenswert.

## 16. Fehlervertrag

| Status/Fehler | Bedeutung und Clientreaktion |
|---|---|
| HTTP 200 | erfolgreiche Antwort; Inhalt und Vertrag trotzdem validieren |
| HTTP 401 | `APP_TOKEN` ist gesetzt und der Suchrequest hat kein passendes `X-GenericParser-Token`; nicht ohne korrigierte Zugangsdaten wiederholen |
| HTTP 409 | Selbsttest nicht aktiviert |
| HTTP 422 | JSON oder Modulmodell ungültig; Request korrigieren, nicht automatisch wiederholen |
| HTTP 500 JSON | Fehler im Modul-/Referenzpfad; `phase`, `error_type`, `ray_id` und `worker` protokollieren |
| HTTP 503 HTML | vorgelagerte Cloudflare-/Abrufantwort statt API-JSON; mit Pause behandeln |
| Cloudflare 1027 | tägliches Free-Anfragekontingent überschritten |
| Cloudflare 1102 | aktuelles Cloudflare-Signal für überschrittenes CPU- oder Speicherlimit |
| historisch beobachtetes 1101 | unbehandelte Worker-Ausnahme beziehungsweise Abbruch vor der ASGI-Antwort |

Fehlerantwort 0.45.0:

```json
{
  "detail": "Modulsuche konnte nicht verarbeitet werden.",
  "retryable": false,
  "error_type": "RuntimeError",
  "phase": "module_v1_search",
  "ray_id": "...",
  "worker": {}
}
```

`retryable: false` bedeutet, dass der Server keinen sicheren sofortigen Retry zusagt. Die PWA-Referenz verwendet für bestimmte terminale Cloudflare-Ketten dennoch eine einmalige, zeitversetzte Browser-Recovery. Diese Recovery ist keine API-Garantie und war in längeren Live-Suchen nicht zuverlässig.

## 17. Cloudflare Workers Free: Grenzen und konkrete Auswirkungen

Offizielle Cloudflare-Grenzen mit Stand 2026-08-05:

| Grenze | Workers Free | Auswirkung auf GenericParser |
|---|---:|---|
| dynamische Requests | 100.000 pro Tag, Reset 00:00 UTC | PWA-, API- und Projektaufrufe teilen das Kontingent |
| CPU-Zeit je HTTP-Aufruf | 10 ms | Python/Pyodide, Parsing und Bewertung müssen pro Paket sehr klein bleiben |
| Speicher je Isolat | 128 MB | kein großer DOM und keine dauerhafte In-Memory-Sammlung |
| Subrequests je Aufruf | 50 | der aktive Pfad verwendet regulär einen Kleinanzeigen-Seitenabruf; Redirects zählen zusätzlich |
| gleichzeitig wartende ausgehende Verbindungen | 6 | parallele Quellenabrufe sind nicht Teil von 0.45.0 |
| komprimierte Workergröße | 3 MB | Abhängigkeiten und Python-Bundle müssen klein bleiben |
| Startzeit des globalen Scopes | 1 Sekunde | Imports werden lazy gehalten; schwere Initialisierung ist ungeeignet |
| Logdaten je Request | 256 KB | Debugereignisse sind begrenzt und Payloadlogging standardmäßig aus |
| Variablen/Secrets | 64 je Worker, je 5 KB | `APP_TOKEN` liegt deutlich darunter |

Offizielle Quellen:

- <https://developers.cloudflare.com/workers/platform/limits/>
- <https://developers.cloudflare.com/workers/platform/pricing/>
- <https://developers.cloudflare.com/workers/languages/python/how-python-workers-work/>
- <https://developers.cloudflare.com/workers/languages/python/stdlib/>

Cloudflare misst CPU-Zeit ohne reine Wartezeit auf Netzwerkantworten. Das hilft beim Kleinanzeigen-Abruf, schützt aber nicht vor CPU-Kosten durch Pyodide-Start, FastAPI/Pydantic und HTML-Auswertung.

### 17.1 Warum sieben Karten pro Request

Die Begrenzung ist eine technische Schutzmaßnahme für die 10-ms-CPU-Grenze. Sie ist kein fachliches Ergebnislimit. Vollständigkeit entsteht nur durch mehrere sequenzielle Requests und Deduplizierung im Client.

### 17.2 Warum fünf Sekunden Pause

Die Pause ist eine projektspezifische Schonmaßnahme zwischen Paketen. Sie ist keine Cloudflare-Vorgabe und garantiert weder Freigabe durch Kleinanzeigen noch die Erholung eines beendeten Worker-Isolats.

### 17.3 Bekannte Grenzen im Free-Betrieb

- Lange Suchläufe können trotz kleiner Pakete mit 503 beziehungsweise Worker-Ausnahmen abbrechen.
- Die einmalige Browser-Recovery aus 0.44.6.5 kann erneut am selben Plattformzustand scheitern.
- Es gibt keine serverseitige Queue, kein Durable Object, keinen Cron-Suchlauf und keine garantierte Fortsetzung.
- Der Suchstand liegt im aufrufenden Client. Ein gelöschter Browserstand, Gerätewechsel oder privater Modus kann ihn verlieren.
- Eine dynamische Quellseite kann zwischen Arbeitspaketen neue, entfernte oder umsortierte Anzeigen liefern.
- Kleinanzeigen stellt für diesen Parser keinen zugesicherten öffentlichen Vertrag bereit. HTML-, URL- oder Schutzmechanismusänderungen können Abruf und Extraktion brechen.
- `reported_total` kann fehlen, gerundet oder widersprüchlich sein.
- Debugmodus erhöht Antwortgröße und CPU-Arbeit geringfügig und sollte nicht dauerhaft aktiv sein.

### 17.4 Nicht durch 0.45.0 zugesichert

- garantiert vollständige Erfassung aller Kleinanzeigen-Ergebnisse,
- garantierte automatische Wiederaufnahme nach Plattformabbruch,
- parallele Massensuchen für Evercade und SNES,
- Detailseiten- oder Verkäuferanalyse,
- persistente Serverdatenbank,
- Preisalarm oder Benachrichtigung,
- weitere Quellen wie eBay oder Vinted,
- garantierte Verfügbarkeit oder SLA.

## 18. Python-Bibliotheksschnittstelle

Die Profilmodelle und Adapter können ohne HTTP direkt importiert werden:

```python
from generic_parser import (
    ModuleDebugOptions,
    ModulePageRequest,
    ModuleSearchProfile,
    evercade_profile,
    snes_pal_profile,
)
```

Die eigentliche Cloudflare-Suche wird über den HTTP-Endpunkt empfohlen. Direkte Nutzung interner versionierter Module wie `search_service_v0450` ist kein stabiler Bibliotheksvertrag.

## 19. Kompatibilität und Releasepflicht

Innerhalb von `generic-parser-module-v1` dürfen optionale Antwortfelder ergänzt werden. Clients müssen unbekannte Felder ignorieren. Entfernen, Umbenennen oder semantisches Ändern verpflichtender Felder erfordert einen neuen Vertragsnamen beziehungsweise einen neuen API-Pfad.

Ab 0.45.0 muss jedes Release gemeinsam liefern:

- einen versionsgebundenen vollständigen API-Snapshot,
- aktualisierte Funktions- und Limitierungsbeschreibung,
- Release Notes und Changelog,
- strukturierte Einträge in `VERSION.json`,
- lokalen und GitHub-CI-Nachweis,
- Cloudflare-Liveprüfung oder einen ausdrücklich dokumentierten offenen Blocker,
- gepflegte Download-, Commit- und Rollbackreferenzen.

Der verbindliche Ablauf steht in [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).
