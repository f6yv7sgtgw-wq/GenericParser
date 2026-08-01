# Kleinanzeigen-Parser bauen: Referenz für ein KI-Modell

**Was du mit diesem Dokument tun sollst:** Du sollst einen Bot bauen, der
kleinanzeigen.de regelmäßig nach bestimmten Produkten durchsucht und den Nutzer bei
Treffern benachrichtigt. Dieses Dokument enthält alles, was du über das Parsen der
Plattform wissen musst. Quellcode einer Referenz-Implementierung bekommst du nicht —
du baust von Grund auf.

**Bevor du Code schreibst:** stelle dem Nutzer die Fragen aus §1. Ohne die Antworten
sind zentrale Entscheidungen (Ort, Radius, Integrationsform, Benachrichtigungsweg)
geraten, und geraten heißt hier: unbrauchbar.

---

## 1. Fragen an den Nutzer — zuerst stellen

Frage kompakt, gebündelt, mit sinnvollen Vorschlägen. Nicht alle einzeln nacheinander.

### 1.1 Pflichtfragen

**Ort und Umkreis**
- Von welcher Postleitzahl (oder welchem Ort) aus soll gesucht werden?
- Welcher Radius in km? (typisch 20–50; alles über 100 macht Abholung meist unwirtschaftlich)
- Ist Versand akzeptabel, oder nur Abholung? Das ändert, ob der Radius überhaupt eine harte Grenze ist.

**Was gesucht wird**
- Welche Produkte konkret? Marke und Modell, wenn bekannt.
- Preisobergrenze pro Produkt oder global?
- Auch defekte Geräte / Bastlerware interessant, oder nur funktionsfähig?
- Sollen „Zu verschenken"-Anzeigen mit rein?
- Sind Konvolute / Sammlungen / Haushaltsauflösungen interessant? (§6.5 — oft die besten Deals,
  brauchen aber eigene Logik)

**Integration**
- Wie soll der Parser laufen?
  - einmaliges CLI-Skript (manuell gestartet)
  - Dauerläufer als systemd-Service / Docker-Container
  - Cronjob in festem Intervall
  - Bibliothek/Modul, das in etwas Bestehendes eingebunden wird
- Wo läuft das? (Dauerläufer auf schwacher Hardware wie einem Einplatinenrechner ist möglich,
  begrenzt aber Optionen wie lokale LLM-Bewertung oder Bildanalyse)
- Wie oft prüfen? (5–10 Minuten ist der sinnvolle Bereich, siehe §8.2)

**Benachrichtigung**
- Wohin? (Messenger, E-Mail, Push-Dienst, Webhook, Desktop-Notification, nur Logdatei)
- Existiert dafür schon etwas Nutzbares (laufender API-Container, Bot-Token, SMTP-Zugang),
  oder muss das mit aufgesetzt werden?
- Sofort bei jedem Treffer, oder gesammelt (z. B. stündliche Zusammenfassung)?

### 1.2 Fragen, die du nur bei Bedarf stellst

- Soll der Marktwert automatisch ermittelt werden (Preisvergleich gegen andere Plattformen),
  oder pflegt der Nutzer je Produkt einen Richtwert von Hand? *Automatik braucht in der Regel
  einen API-Zugang, der beantragt werden muss — frage, ob so etwas vorliegt, bevor du darauf baust.*
- Soll ein LLM die Grenzfälle bewerten (§7)? Wenn ja: lokales Modell oder API? Das ist optional;
  ein guter Parser funktioniert ohne.
- Persistenz: SQLite-Datei reicht fast immer. Nur fragen, wenn Mehrbenutzerbetrieb im Spiel ist.

### 1.3 Was du **nicht** fragst, sondern selbst löst

Die Location-ID (§2.2), Selektor-Details, Retry-Strategie, Datenmodell. Der Nutzer soll
Produkt und Umgebung beschreiben, nicht deine Implementierung.

---

## 2. Wie die Suche aufgebaut ist

### 2.1 URL-Grammatik

Basis: `https://www.kleinanzeigen.de`

Zwei Suchformen, beide bestätigt funktionierend:

```
# Keyword-Suche
https://www.kleinanzeigen.de/s-{PLZ}/{keyword-slug}/k0l{LOCATION_ID}r{RADIUS_KM}

# Kategorie-Suche
https://www.kleinanzeigen.de/{KATEGORIE_PFAD}/k0l{LOCATION_ID}r{RADIUS_KM}
```

Der Code-Block am Ende wird **ohne Trennzeichen zusammengeschrieben**:

| Segment | Bedeutung |
|---------|-----------|
| `k0`    | Keyword-ID (0 = keine gespeicherte Suche) |
| `c{id}` | Kategorie-ID, numerisch — optional |
| `l{id}` | **Location-ID** (nicht die PLZ!) |
| `r{km}` | Radius in km |

Der `{keyword-slug}`: lowercase, Leerzeichen → Bindestrich. Umlaute funktionieren, aber
transliteriere sie (`ä→ae, ö→oe, ü→ue, ß→ss`) — das ist robuster gegen Encoding-Probleme
in URLs.

### 2.2 Location-ID ≠ Postleitzahl

Die häufigste Fehlerquelle überhaupt. Kleinanzeigen nutzt intern numerische Orts-IDs, die
nichts mit der PLZ zu tun haben. Setzt du die PLZ an die `l`-Stelle, wird der Radius
still ignoriert und du bekommst bundesweite Ergebnisse — der Bot läuft scheinbar
korrekt und liefert unbrauchbare Treffer.

Ermittlung, in dieser Reihenfolge:

1. **Nutzer fragen**, falls er die ID schon kennt (steht in der URL, wenn er auf der
   Website einmal mit Ortsangabe sucht — das `l{ZAHL}` daraus).
2. **Automatisch ermitteln:** Kleinanzeigen hat einen Autocomplete-Endpunkt für die
   Ortssuche. Finde ihn, indem du im Browser die Netzwerkanfragen beim Tippen im
   Ortsfeld beobachtest, und cache das Ergebnis dauerhaft in der Konfiguration.
3. **Fallback:** eine Suche mit PLZ absetzen und die Location-ID aus der Redirect-URL
   oder aus dem HTML der Ergebnisseite extrahieren.

Die ID ändert sich nicht. Einmal ermitteln, in die Config schreiben, fertig.

**Verifiziere die ID**, bevor du sie verwendest: Suche mit Radius 5 km und ohne Radius
gegeneinander laufen lassen. Wenn beide gleich viele Treffer liefern, ist die ID falsch
oder der Radius wirkt nicht.

### 2.3 Zusätzliche Filter — verifizieren, nicht annehmen

Diese Pfadsegmente sind gebräuchlich, aber **du musst sie empirisch prüfen**, bevor du
dich darauf verlässt:

```
/s-{kategorie}/anzeige:angebote/k0l{ID}r{KM}     # nur Angebote, keine Gesuche
/s-{kategorie}/preis:20:200/k0l{ID}r{KM}         # Preisspanne
/s-{kategorie}/anbieter:privat/k0l{ID}r{KM}      # nur Privatverkäufer
/s-{kategorie}/seite:2/k0l{ID}r{KM}              # Pagination
?sortingField=SORTING_DATE                        # Sortierung als Query-Parameter
```

**Prüfprozedur — immer durchführen:**

1. URL *mit* Filter abrufen, Ergebniskarten zählen → `n_gefiltert`
2. Identische URL *ohne* Filter, zählen → `n_roh`
3. Wähle dafür eine Suche, die garantiert Ausschuss enthält (bei `anzeige:angebote`
   z. B. ein Begriff mit vielen Gesuchen). Ist `n_gefiltert == n_roh`, wurde der
   Filter **ignoriert**.
4. Stichprobe: fünf Karten manuell gegen die Filterbedingung prüfen.

Kleinanzeigen wirft bei unbekannten Pfadsegmenten **keinen Fehler** — es ignoriert sie
stillschweigend. Ein still ignorierter Filter ist schlimmer als gar keiner, weil der
nachgelagerte Code dann annimmt, er müsse nicht mehr selbst filtern.

### 2.4 Kategorie oder Keyword?

- **Keyword**, wenn ein konkretes Produkt gesucht wird („Beispielmarke XY-500").
- **Kategorie**, wenn eine ganze Klasse überwacht wird („alles Werkzeug unter 50 €",
  „alles Verschenkbare in der Nähe").
- **Beides parallel** ist die beste Abdeckung: Kategorie fängt Inserate mit schlecht
  formulierten Titeln, Keyword fängt Inserate außerhalb der erwarteten Kategorie
  (Verkäufer sortieren oft falsch ein).

Bekannte Kategorie-Pfade:
`/s-zu-verschenken-tauschen`, `/s-werkzeug`, `/s-elektronik`, `/s-computer`,
`/s-handys-smartphones`, `/s-fahrraeder-zubehoer`, `/s-haushaltsgeraete`,
`/s-garten-pflanzen`, `/s-musik-instrumente`, `/s-sport-fitness`,
`/s-wohnen-einrichten`, `/s-spielzeug-kinderbedarf`, `/s-autos`,
`/s-kleidung-accessoires`

Weitere findest du, indem du die Kategorienavigation der Website abgehst. Prüfe jeden
Pfad einmal, bevor du ihn in die Config schreibst.

---

## 3. HTML der Ergebnisliste

### 3.1 Bestätigte Selektoren

Stand der letzten Verifikation. Klassennamen ändern sich gelegentlich — siehe §3.3.

| Was | Selektor |
|-----|----------|
| eine Ergebniskarte | `article.aditem` |
| Inserat-ID | Attribut `data-adid` am `article` |
| Titel + Link | `a.ellipsis` (Text = Titel, `href` = relativer Pfad) |
| Preis | `p.aditem-main--middle--price-shipping--price` |
| PLZ + Ort | `div.aditem-main--top--left` |
| Zeitstempel | `div.aditem-main--top--right` |

Der `href` ist relativ (`/s-anzeige/...`) — Basis-URL davorsetzen.

### 3.2 Wahrscheinlich vorhanden, prüfen

| Was | Selektor (Hypothese) | Warum wichtig |
|-----|---------------------|---------------|
| Beschreibungs-Anriss | `p.aditem-main--middle--description` | **sehr wertvoll** |
| Tags („Versand möglich", „Gesuch") | `span.simpletag` | Gesuch-Erkennung |
| Vorschaubild | `img` innerhalb der Karte | Bild-URL, oft lazy-loaded |

Der Beschreibungs-Anriss ist der wichtigste Fund: er kostet **keinen zusätzlichen
HTTP-Request** und enthält häufig Modellnummer, Zustand und Hinweise wie „defekt".
Wenn er existiert, halbiert er die Zahl der nötigen Detailseiten-Abrufe. Suche gezielt
danach, bevor du auf Detailseiten ausweichst.

### 3.3 Robustheit gegen Layout-Änderungen

Baue eine Sanity-Prüfung ein, die drei Fälle unterscheidet, wenn null Karten gefunden werden:

| Fall | Erkennungsmerkmal | Reaktion |
|------|-------------------|----------|
| echt keine Treffer | Seitentext enthält sinngemäß „keine Anzeigen gefunden" | normal, weiter |
| Selektor tot | HTML groß, aber kein `aditem` und kein Nulltreffer-Hinweis | **Wartungs-Alarm** |
| geblockt / CAPTCHA | HTTP 403/429 oder Challenge-Seite | Backoff, §8.2 |

Ohne diese Unterscheidung läuft der Bot nach einem Layout-Wechsel wochenlang stumm
weiter, und alle Beteiligten glauben, es gäbe einfach keine Angebote. Das ist der
häufigste Totalausfall solcher Bots.

### 3.4 Duplikate

Bezahlte „TOP"-Inserate erscheinen zusätzlich am Listenanfang — **dieselbe `data-adid`
zweimal auf einer Seite**. Dedupliziere immer:

- innerhalb eines Durchlaufs über ein `set` der IDs,
- über Durchläufe hinweg gegen die Datenbank.

`data-adid` ist über die Lebenszeit des Inserats stabil. „Nach oben setzen" ändert die ID
**nicht**, aber den Zeitstempel — dedupliziere also niemals über Zeitstempel oder Titel.

---

## 4. Felder normalisieren

Rohtext ist kein Datum und kein Preis. Diese Normalisierung ist Pflicht, sonst
funktionieren alle nachgelagerten Filter falsch.

### 4.1 Preis

| Rohtext | `preis` | Flags |
|---------|---------|-------|
| `120 €` | `120.0` | — |
| `120 € VB` | `120.0` | `verhandelbar` |
| `1.250 €` | `1250.0` | — |
| `1.250,50 €` | `1250.5` | — |
| `Zu verschenken` | `0.0` | `gratis` |
| `VB` (ohne Zahl) | `None` | `verhandelbar`, `preis_unbekannt` |
| leer | `None` | `preis_unbekannt` |
| `1 €` | `1.0` | `verdaechtig_niedrig` |

**Deutsches Zahlformat:** erst Tausenderpunkt entfernen, **dann** Dezimalkomma zu Punkt.
Die umgekehrte Reihenfolge macht aus `1.250,50` den Wert `1.25` oder `1250250` — ein
stiller Fehler, der Preisfilter komplett aushebelt.

**Drei Zustände, nicht zwei.** `preis = 0` (verschenkt), `preis = None` (unbekannt) und
`preis = 50` sind fachlich verschieden. In vielen Sprachen ist eine Prüfung wie
`if not preis` für die ersten beiden Fälle wahr — genau dort entstehen die falschen
Alerts. Prüfe explizit auf `None`.

**`None` ist nicht „günstig".** Ein Inserat ohne Preisangabe darf nicht durch den
Maximalpreis-Filter rutschen, als wäre es gratis. Entscheide bewusst, ob preislose
Inserate durchgelassen werden (bei „Zu verschenken"-Suchen ja, sonst meist nein).

**`1 €` ist meist kein Preis**, sondern der „Preis auf Anfrage"-Trick. Markieren,
nicht blind als Schnäppchen werten.

### 4.2 Datum

Formate: `Heute, 14:32` · `Gestern, 09:11` · `27.07.2026`

Sofort in absolutes ISO-Datetime umrechnen, relativ zur **lokalen deutschen Zeitzone
(Europe/Berlin)**, nicht UTC — sonst kippt die Auflösung von „Heute" um Mitternacht
Sommerzeit auf den falschen Tag.

Aktualität ist beim Deal-Jagen das entscheidende Signal: ein gutes Angebot, das zwei
Tage alt ist, ist praktisch immer weg. Nutze das Alter als **Score-Multiplikator**,
nicht als Hardfilter — ein 6 Stunden altes, unterbewertetes Inserat ist immer noch
einen Alert wert. Ausnahme: der allererste Lauf (§8.1).

### 4.3 Ort

Rohtext: `12345 Musterstadt (12 km)` oder ohne Distanzangabe.
Zerlege in `plz`, `ort`, `distanz_km` (optional). Die Distanz fehlt bei Suchen ohne Radius.

Bei Abholware ist die Distanz ein harter Kostenfaktor. Rechne die Fahrt in die
Deal-Bewertung ein — 80 km für ein 20-€-Gerät lohnt nicht, auch wenn die Marge
prozentual gut aussieht. Wenn der Nutzer Versand akzeptiert (§1.1), gilt das nur für
Inserate ohne Versandoption.

---

## 5. Datenmodell

Minimum pro Inserat:

```
id              # data-adid, Primärschlüssel
titel
preis           # normalisiert, nullable
preis_flags     # Liste, siehe 4.1
preis_raw       # Originaltext, für Debugging unverzichtbar
url             # absolut
plz, ort, distanz_km
inseriert_am    # ISO-Datetime
beschreibung    # Anriss oder Volltext, nullable
quelle          # welche Suche/welches Keyword hat es gefunden
zuerst_gesehen  # ISO-Datetime
```

Persistenz: eine eingebettete Datenbank (SQLite o. ä.) reicht. Drei getrennte Zustände,
das ist wichtig:

| Konzept | Zweck |
|---------|-------|
| gesehene Inserate | Dedup über Durchläufe |
| verschickte Alerts | verhindert Doppel-Benachrichtigung |
| Preishistorie | ermöglicht Alert bei Preissenkung (§8.4) |

**„Gesehen" ist nicht „alarmiert".** Getrennt speichern. Wenn der Alert-Versand
fehlschlägt (Dienst nicht erreichbar), darf das Inserat nicht als alarmiert markiert
werden — sonst ist der Treffer für immer verloren. Reihenfolge: senden → Erfolg
prüfen → erst dann markieren.

**Reihenfolge beim Verarbeiten:** prüfen, ob neu → verarbeiten → speichern.
Wer zuerst speichert und dann „ist es neu?" fragt, macht jedes Inserat sofort alt und
alarmiert nie.

---

## 6. Das Produktmodell — der eigentliche Kern

### 6.1 Ein gesuchtes Produkt ist kein String

Die naive Lösung — Suchbegriff als Teilstring im Titel prüfen — erzeugt **beide**
Fehlerarten gleichzeitig:

- **Falsch positiv:** Suchbegriff `akku` trifft „Ersatz**akku** defekt",
  „Bohrmaschine ohne **Akku**", „**Akku**staubsauger".
- **Falsch negativ:** Suchbegriff `XY 500` trifft **nicht** „Beispielmarke XY500
  Professional" (andere Schreibweise) und nicht „Beispielmarke Akkuschrauber blau 18 V"
  (Modellnummer steht nur in der Beschreibung).

Modelliere ein Produkt stattdessen als Objekt:

```json
{
  "id": "beispiel-modell-xy",
  "anzeigename": "Beispielmarke XY-500 Akkuschrauber",
  "marke": ["beispielmarke", "beispiel-marke"],
  "produkttyp": ["akkuschrauber", "bohrschrauber", "schlagbohrschrauber"],
  "modell_muster": ["xy\\s*-?\\s*500", "xy500"],
  "muss_enthalten": { "irgendeins_von": ["beispielmarke"] },
  "darf_nicht_enthalten": ["defekt", "bastler", "ersatzteil", "nur karton", "nachbau"],
  "such_queries": [
    "beispielmarke xy500",
    "beispielmarke xy 500",
    "beispielmarke akkuschrauber"
  ],
  "preis_max": 90,
  "marktwert_richtwert": 140,
  "akzeptiere_konvolut": true,
  "akzeptiere_unvollstaendig": false
}
```

Diese Struktur füllst du gemeinsam mit dem Nutzer aus §1.1 aus. Frag nach Marke und
Modell — den Rest (Muster, Synonyme, Negativliste) leitest du selbst ab und legst es
ihm zur Bestätigung vor.

### 6.2 Queries generieren (Abdeckung)

Aus einem Produkt entstehen **mehrere** Plattform-Queries:

- Marke + Modellnummer zusammen: `beispielmarke xy500`
- Marke + Modellnummer getrennt: `beispielmarke xy 500` — Verkäufer tippen beide Varianten
- Marke + Produkttyp: `beispielmarke akkuschrauber` — fängt Inserate ohne Modellnummer
- Nur Produkttyp: lohnt nur bei Nischenbegriffen; bei häufigen Typen zu viel Rauschen

Füttere die Plattform-Suche **nicht** mit Ausschlüssen. Kleinanzeigen hat keine
zuverlässige Minus-Syntax. Ausschluss passiert lokal.

Merke: **Die Plattform liefert Abdeckung, du lieferst Genauigkeit.** Zu strenge
Plattform-Queries kosten dich die guten Deals — die stecken oft in schlecht
formulierten Inseraten. Zu lasche lokale Filter kosten dich das Vertrauen des Nutzers,
weil er nach dem fünften Fehlalarm die Benachrichtigungen ignoriert.

### 6.3 Modellnummern zuverlässig matchen

Der stärkste Einzelindikator. Normalisiere Titel **und** Beschreibung vorher:

1. lowercase
2. Umlaute transliterieren (`ä→ae` usw.)
3. alle Nicht-Alphanumerischen Zeichen (Bindestrich, Punkt, Slash) → Leerzeichen
4. Mehrfach-Leerzeichen zusammenfassen

Bilde zusätzlich eine **entkernte Variante ohne jedes Leerzeichen** und prüfe die
Modellmuster gegen beide Formen. Damit matchen `XY-500`, `XY 500`, `xy500` und
`XY500N` einheitlich.

**Suffixe beachten.** Bei Werkzeug und Elektronik kodieren Modellsuffixe häufig den
Lieferumfang (mit/ohne Akku, mit/ohne Koffer, Anzahl Akkus). Das macht schnell die
Hälfte des Preises aus. Wenn der Nutzer Vollständigkeit verlangt, müssen Signale wie
`solo`, `body only`, `ohne akku`, `nur maschine`, `nur gerät` den Treffer entwerten.
Frag den Nutzer bei markenspezifischen Suffix-Systemen, welche Variante er will.

### 6.4 Negativ-Vokabular

Universell auszuschließen:

- **Gesuche:** `suche`, `gesucht`, `wer hat`, `wer verkauft`, `tausche gegen`, `ankauf`
- **Stellenanzeigen:** `(m/w/d)`, `m/w/d`, `stellenangebot`, `wir suchen`, `minijob`, `aushilfe`
- **Nicht das Produkt:** `ersatzteil`, `zubehör`, `adapter`, `hülle`, `tasche`,
  `nur koffer`, `leergehäuse`, `anleitung`, `aufkleber`, `karton`, `verpackung`
- **Zustand:** `defekt`, `bastler`, `bastlerware`, `teildefekt`, `kaputt`,
  `funktioniert nicht`, `zum ausschlachten`, `als ersatzteil`
- **Klone:** `nachbau`, `replica`, `kompatibel mit`, `passend für`, `no name`

Ergänze kategoriespezifisch (bei Elektronik z. B. `displaybruch`, `für teile`,
gesperrte Geräte; bei Fahrrädern `nur rahmen`).

**Wo prüfen:** Titel **und** Beschreibung. „Produkt XY500" im Titel und „Motor
durchgebrannt, für Bastler" in der Beschreibung ist ein sehr häufiges Muster — im
reinen Titel-Matching unsichtbar.

**Negation beachten.** Blindes Teilstring-Matching auf `defekt` verwirft auch
„läuft einwandfrei, **nicht defekt**" und „Bohrer defekt, Maschine top". Prüfe bei
einem Negativ-Treffer ein Fenster von etwa vier Wörtern davor auf Verneinung
(`nicht`, `kein`, `nie`, `keinerlei`). Wenn dir das zu fehleranfällig wird, ist das
genau der Fall für die optionale LLM-Stufe (§7) — nicht für immer komplexere Regex.

### 6.5 Gesuch vs. Angebot

Der wichtigste Einzelfilter und der, der am häufigsten vergessen wird. Kleinanzeigen
mischt Gesuche („Suche Akkuschrauber") in die normale Ergebnisliste. Erkennung in
dieser Reihenfolge:

1. URL-Filter `anzeige:angebote`, **falls du seine Wirksamkeit verifiziert hast** (§2.3)
2. Tag-Element auf der Karte mit Text „Gesuch"
3. Titel-Heuristik: beginnt mit `suche`, `such `, `gesucht`, `ankauf`, `kaufe`
4. Detailseite: Gesuche haben eine abweichende Darstellung (kein Versandfeld o. ä.)

Verlass dich nicht allein auf die Titel-Heuristik: „Suche Werkstattauflösung" ist ein
Gesuch, „Werkzeug aus Auflösung, Sammler gesucht" ist ein Angebot. Das Wort steht in
beiden.

### 6.6 Konvolute und Bundles

„Werkzeugkiste voll, Nachlass, 50 €" ist häufig der beste Deal überhaupt — und fällt
durch jedes Modellnummer-Matching, weil kein einzelnes Modell genannt wird.

Erkenne Bundle-Signale: `konvolut`, `sammlung`, `nachlass`, `auflösung`, `posten`,
`restposten`, `alles zusammen`, `kiste`, `paket`, `diverse`, `sammelauflösung`.

Behandle sie als **eigene Alert-Klasse** mit anderer Frage: nicht „ist das Produkt X",
sondern „ist plausibel etwas Wertvolles dabei und ist der Gesamtpreis niedrig".
Für genau diese Klasse lohnt sich Bildauswertung am meisten (§7.4) — auf dem Foto sind
Marken und Umfang oft eindeutig erkennbar, im Text nie.

Frag den Nutzer in §1.1, ob er diese Klasse überhaupt will. Sie erzeugt mehr Alerts
mit geringerer Trefferquote, dafür die größeren Fänge.

---

## 7. Filterpipeline

```
  Ergebniskarten (100–300 pro Durchlauf)
        │
   [1]  ├─ Billigfilter — reine Stringoperationen, 0 Requests
        │    schon gesehen? · Gesuch? · Stellenanzeige? · Preis über Limit?
        │    · Negativ-Token im Titel?
        │    → entfernt typischerweise ~85 %
        ▼
   [2]  ├─ Kandidaten-Score — Regex auf Titel + Beschreibungsanriss
        │    Marke ✓ · Modellnummer ✓ · Produkttyp ✓ · Preisplausibilität · Frische
        │    → hoher Score + eindeutig: direkt Alert
        │    → unter Schwelle: verwerfen
        │    → Graubereich: weiter
        ▼
   [3]  ├─ Detailseite laden (1 HTTP-Request pro Kandidat)
        │    volle Beschreibung, Attributtabelle, Bild-URLs, Anbietertyp
        │    Negativfilter erneut auf vollem Text
        ▼
   [4]  └─ [optional] LLM-Urteil — nur für den verbleibenden Graubereich
             → strukturiertes JSON mit Confidence
        ▼
      Benachrichtigung
```

**Warum gestuft:** Stufe 3 kostet einen HTTP-Request und damit Rate-Limit-Budget.
Wer für jede der 300 Karten die Detailseite lädt, wird in unter einer Stunde geblockt.
Stufe 4 kostet Rechenzeit oder Geld. Beide dürfen nur sehen, was Stufe 1–2 nicht
eindeutig entscheiden konnten.

### 7.1 Scoring-Skizze

```
score = 0
marke gefunden           → +40    # Pflichtsignal
modellnummer gefunden    → +40    # stärkstes Signal
produkttyp gefunden      → +15
preis <= limit           → +10
preis < richtwert * 0.4  → +15    # auffällig günstig = interessant
gratis                   → +20
inseriert vor < 30 min   → +10
bundle-signal            →  +5    # eigene Klasse, §6.6
negativ-token            → -60    # praktisch tödlich
```

Schwellen als Startpunkt: `>= 70` → Alert · `40–69` → Stufe 3/4 · `< 40` → verwerfen.

**Harte Vorbedingung:** ohne Marken- **oder** Modellnummerntreffer nie alarmieren.
Ein reiner Produkttyp-Match („akkuschrauber") ist bei produktspezifischer Suche
immer zu unscharf.

Kalibriere die Zahlen an echten Daten. Sammle die ersten Tage mit, was durchkommt und
was der Nutzer als Fehlalarm meldet, und zieh die Gewichte danach nach. Die Werte oben
sind ein Startpunkt, kein Ergebnis.

### 7.2 Optionale LLM-Stufe

Nur sinnvoll, wenn der Nutzer sie will (§1.2) und Regex den Graubereich nicht sauber
trennt. Ein guter Parser funktioniert ohne. Wenn du sie baust: gib dem Modell
**strukturierte Felder, kein Roh-HTML**, und erzwinge ein Antwortschema:

```json
{
  "ist_treffer": true,
  "confidence": 0.0,
  "modell_bestaetigt": false,
  "zustand": "neu | gebraucht_gut | gebraucht_stark | defekt | unbekannt",
  "vollstaendig": true,
  "ist_gesuch": false,
  "ist_konvolut": false,
  "warnungen": [],
  "begruendung": "max 200 Zeichen"
}
```

Regeln in den Prompt: Bei Unsicherheit `ist_treffer: false` — ein verpasster Deal
kostet nichts, ein Fehlalarm kostet Vertrauen. „kompatibel mit" / „passend für"
bedeutet Fremdhersteller, also kein Treffer. Preisangaben in der Beschreibung schlagen
den Listenpreis, wenn sie sich widersprechen.

Alarmiere erst ab `confidence >= 0.75`. Logge `begruendung` immer mit — das ist dein
einziges Debugging-Werkzeug, wenn der Bot in drei Wochen Unsinn meldet.

### 7.3 Freitext taugt nicht

Eine Antwort wie „Ja, das sieht passend aus" ist weder schwellwertfähig noch
auswertbar. Mit strukturierter Ausgabe kannst du die Entscheidung speichern, später
auswerten („wie viele 0.8er-Treffer waren echt?") und die Schwelle datenbasiert
nachziehen.

### 7.4 Bilder

Bei Werkzeug, Elektronik und Konvoluten ist das Foto oft aussagekräftiger als der Text.
Lohnt sich für: Konvolute, Inserate ohne Modellnummer im Text, Zustandsprüfung
(Rost, Bruch, fehlende Teile). Lohnt sich nicht für textlich eindeutige Inserate.

Reihenfolge: erst Texturteil, Bild nur nachladen, wenn die Confidence im Graubereich
(etwa 0.4–0.75) liegt. Kläre vorher, ob die Zielhardware das leisten kann (§1.1).

---

## 8. Betrieb — was solche Bots in der Praxis zerstört

### 8.1 Der erste Lauf

Beim allerersten Start sind **alle** Inserate neu. Ohne Vorkehrung feuert der Bot
sofort hunderte Benachrichtigungen und der Nutzer schaltet ihn ab, bevor er je
funktioniert hat.

Lösung: Der erste Durchlauf schreibt nur in die Datenbank und alarmiert nicht
(Baseline-Lauf). Dasselbe gilt **nach jedem Hinzufügen eines neuen Suchbegriffs** —
der hat noch keine Historie. Praktikable Regel: neue Suchbegriffe werden erst ab dem
zweiten Durchlauf alarmberechtigt, oder beim ersten Mal nur für Inserate der letzten
zwei Stunden.

### 8.2 Rate Limiting

- **Sequenziell** abrufen, nie parallel. Genau eine offene Verbindung.
- Zufälliger Delay von einigen Sekunden **zwischen HTTP-Requests**.
  Ein Delay, der stattdessen in der Schleife über geparste Karten steht, schläft je
  nach Trefferzahl völlig unterschiedlich lang — bei 200 Treffern minutenlang, bei
  null Treffern gar nicht. Genau falsch herum. Das Delay gehört an den Request.
- User-Agent rotieren, realistische Browser-Header setzen
  (`Accept-Language: de-DE,de;q=0.9`).
- Bei HTTP 429 oder 503: lange Pause (Größenordnung 30 Minuten) und bei Wiederholung
  **exponentiell** verlängern.
- Poll-Intervall 5–10 Minuten. Häufiger bringt kaum zusätzliche Deals, aber deutlich
  mehr Blockrisiko.
- Timeouts setzen und Retries begrenzen (3 Versuche mit steigender Wartezeit).

### 8.3 Robuste Fehlerbehandlung

Ein Parse-Fehler in einer einzelnen Karte darf nie den ganzen Durchlauf abbrechen.
Fehler pro Karte fangen, protokollieren, weitermachen. Aber: wenn **alle** Karten
fehlschlagen, ist das ein Layout-Wechsel und muss gemeldet werden (§3.3).

### 8.4 Preisänderungen

Verkäufer senken Preise. Ein Inserat, das gestern bei 200 € uninteressant war, kann
heute bei 60 € ein Volltreffer sein — aber es ist nicht mehr „neu" und wird nie wieder
betrachtet.

Speichere den Preis pro Inserat und alarmiere erneut bei signifikantem Rückgang
(Faustwert: über 25 %, und erst wenn der neue Preis unter dem Limit liegt). Das ist
eine der ertragreichsten Erweiterungen überhaupt und wird fast immer vergessen.

### 8.5 Der Alert-Text

Der Nutzer muss ohne Öffnen der Anzeige entscheiden können. Reihenfolge:
**Was · Preis · Wo/Wann · Warum interessant · Link.**

```
Beispielmarke XY-500 · 65 € (VB)
Musterstadt, 12 km · vor 4 Minuten
Zustand: gebraucht, gut · vollständig
Richtwert ~140 € → Differenz ~75 €
https://www.kleinanzeigen.de/s-anzeige/...
```

Kein Fließtext, kein Emoji-Rauschen, keine Zusammenfassung der Beschreibung.
Bei guten Deals zählt jede Sekunde. Wenn der Nutzer gesammelte Benachrichtigungen
gewählt hat (§1.1), sortiere innerhalb der Zusammenfassung nach Score, nicht nach Zeit.

---

## 9. Abnahmetest

Prüfe **an echten Ergebnissen**, bevor du die Implementierung als fertig meldest.
Jeder Punkt einzeln, mit einem konkreten Inserat belegt:

- [ ] Ein Gesuch („Suche <Produkt>") wird nicht alarmiert.
- [ ] Eine Stellenanzeige mit `(m/w/d)` wird nicht alarmiert.
- [ ] „Ersatzakku für <Produkt>" wird nicht als das Produkt selbst alarmiert.
- [ ] Verschiedene Schreibweisen der Modellnummer (`XY-500`, `XY 500`, `xy500`) matchen alle.
- [ ] „<Produkt> defekt, für Bastler" wird abgelehnt.
- [ ] „läuft einwandfrei, nicht defekt" wird **nicht** vom Defekt-Filter abgelehnt.
- [ ] Ein „defekt"-Hinweis, der nur in der Beschreibung steht, wird gefunden.
- [ ] `1.250 €` wird als 1250.0 geparst.
- [ ] Ein Inserat ohne Preisangabe rutscht nicht durch den Maximalpreis-Filter.
- [ ] „Zu verschenken" (0) wird von „kein Preis" (unbekannt) unterschieden.
- [ ] Ein doppelt gelistetes TOP-Inserat erzeugt genau einen Alert.
- [ ] Ein fehlgeschlagener Benachrichtigungsversand markiert das Inserat **nicht** als alarmiert.
- [ ] Der erste Lauf erzeugt keine Alert-Flut.
- [ ] Bei null gefundenen Karten wird zwischen „keine Ergebnisse", „Selektor tot"
      und „geblockt" unterschieden.
- [ ] Der Radius wirkt tatsächlich (Location-ID verifiziert, §2.2).
- [ ] Der Request-Delay ist unabhängig von der Trefferzahl.

---

## 10. Kurzfassung

1. **Zuerst den Nutzer fragen** (§1): Ort, Radius, Produkte, Preisgrenzen,
   Integrationsform, Benachrichtigungsweg.
2. Location-ID ermitteln und verifizieren — nicht die PLZ verwenden.
3. Breit suchen (Keyword **und** Kategorie), streng lokal filtern.
4. Gesuche und Stellenanzeigen zuerst rauswerfen — billigster Genauigkeitsgewinn.
5. Produkt als Objekt modellieren: Marke, Modellmuster, Typ, Negativliste, Preisgrenze.
6. Titel **und** Beschreibung normalisieren (Umlaute, Sonderzeichen, entkernte Variante).
7. Preis, Datum, Ort sauber normalisieren — inklusive aller Sonderfälle aus §4.
8. Gestuft filtern: Regex → Score → (optional) LLM. Teure Stufen sehen nur den Graubereich.
9. Sequenziell abrufen, Delay am Request, HTTP 429 respektieren, Backoff verlängern.
10. Baseline beim ersten Lauf. Alert-Status erst nach erfolgreichem Versand setzen.
11. Preishistorie führen — die zweite Chance bei Preissenkung ist bares Geld.
