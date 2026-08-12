from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import Location, NormalizedPrice, PriceFlag


def _berlin_timezone() -> tzinfo:
    """Liefert Europe/Berlin oder einen sicheren UTC-Fallback ohne tzdata.

    Cloudflare Python Workers/Pyodide enthalten nicht zwingend die IANA-
    Zeitzonendatenbank. Lokal bleibt deshalb die vollständige Berlin-Zeitzone
    mit Sommer-/Winterzeit aktiv; nur in eingeschränkten Laufzeiten wird UTC
    verwendet, damit der Worker bereits beim Import zuverlässig startet.
    """

    try:
        return ZoneInfo("Europe/Berlin")
    except ZoneInfoNotFoundError:
        return timezone.utc


BERLIN = _berlin_timezone()
_TRANSLATION = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
)
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_PRICE_NUMBER_RE = re.compile(r"\d[\d.\s]*(?:,\d{1,2})?")
_LOCATION_RE = re.compile(
    r"^\s*(?P<postal_code>\d{5})\s+(?P<place>.+?)"
    r"(?:\s*\((?P<distance>\d+(?:[.,]\d+)?)\s*km\))?\s*$",
    re.IGNORECASE,
)
_RELATIVE_DATE_RE = re.compile(
    r"^(?P<day>heute|gestern)\s*,?\s*(?P<hour>\d{1,2}):(?P<minute>\d{2})$",
    re.IGNORECASE,
)


def normalize_text(value: str | None) -> str:
    """Normalisiert Text für lokale Filter und Produkt-Matching."""

    if not value:
        return ""
    normalized = value.casefold().translate(_TRANSLATION)
    normalized = _NON_ALNUM_RE.sub(" ", normalized)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def compact_text(value: str | None) -> str:
    """Variante ohne Leerzeichen für Modellnummern wie XY-500, XY 500 und XY500."""

    return normalize_text(value).replace(" ", "")


def parse_price(raw: str | None) -> NormalizedPrice:
    """Parst deutsches Preisformat und erhält fachlich wichtige Sonderzustände."""

    original = (raw or "").strip()
    normalized = normalize_text(original)
    flags: set[PriceFlag] = set()

    if not original:
        return NormalizedPrice(
            raw=original,
            amount=None,
            flags=frozenset({PriceFlag.UNKNOWN}),
        )

    if "vb" in normalized.split() or "verhandlungsbasis" in normalized:
        flags.add(PriceFlag.NEGOTIABLE)

    free_terms = ("zu verschenken", "verschenken", "kostenlos", "gratis")
    if any(term in normalized for term in free_terms):
        flags.add(PriceFlag.FREE)
        return NormalizedPrice(
            raw=original,
            amount=Decimal("0"),
            flags=frozenset(flags),
        )

    match = _PRICE_NUMBER_RE.search(original)
    if match is None:
        flags.add(PriceFlag.UNKNOWN)
        return NormalizedPrice(raw=original, amount=None, flags=frozenset(flags))

    number = match.group(0).replace(" ", "").replace(".", "").replace(",", ".")
    try:
        amount = Decimal(number)
    except InvalidOperation as exc:
        raise ValueError(f"Ungültiger Preis: {original!r}") from exc

    if amount == Decimal("1"):
        flags.add(PriceFlag.SUSPICIOUS_LOW)

    return NormalizedPrice(raw=original, amount=amount, flags=frozenset(flags))


def parse_location(raw: str | None) -> Location:
    """Zerlegt Kleinanzeigen-Ortstext in PLZ, Ort und optionale Entfernung."""

    original = (raw or "").strip()
    if not original:
        return Location(raw=original, postal_code=None, place="", distance_km=None)

    match = _LOCATION_RE.match(original)
    if match is None:
        return Location(raw=original, postal_code=None, place=original, distance_km=None)

    distance_raw = match.group("distance")
    distance = Decimal(distance_raw.replace(",", ".")) if distance_raw else None
    return Location(
        raw=original,
        postal_code=match.group("postal_code"),
        place=match.group("place").strip(),
        distance_km=distance,
    )


def parse_posted_at(raw: str | None, *, now: datetime | None = None) -> datetime | None:
    """Wandelt Kleinanzeigen-Zeitangaben in absolute Zeiten um."""

    original = (raw or "").strip()
    if not original:
        return None

    reference = now or datetime.now(BERLIN)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=BERLIN)
    else:
        reference = reference.astimezone(BERLIN)

    relative = _RELATIVE_DATE_RE.match(original)
    if relative:
        target_date = reference.date()
        if relative.group("day").casefold() == "gestern":
            target_date -= timedelta(days=1)
        return datetime.combine(
            target_date,
            time(
                hour=int(relative.group("hour")),
                minute=int(relative.group("minute")),
            ),
            tzinfo=BERLIN,
        )

    try:
        absolute_date = datetime.strptime(original, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError(f"Unbekanntes Datumsformat: {original!r}") from exc

    return datetime.combine(absolute_date, time.min, tzinfo=BERLIN)


# --- Quellenneutrale Zustands- und Versandcodes ---------------------------
#
# Jeder Marktplatz beschreibt Zustand und Versand in eigenen Worten. Bis 1.7.1
# leitete erst die Browseroberfläche per Regex einen Code aus dem Anzeigetext
# ab, wodurch ein Filter faktisch auf Anzeigestrings matchte. Die Zuordnung
# gehört hierher: der Text bleibt zur Anzeige, der Code trägt die Bedeutung.

CONDITION_CODES = ("new", "like_new", "used", "defective", "unknown")
DELIVERY_MODES = ("free", "available", "pickup", "unknown")

_CONDITION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Reihenfolge entscheidet: "wie neu" darf nicht als "neu" durchgehen, und
    # "neu mit Etikett" ist kein Defekt, nur weil "et" darin vorkommt.
    ("defective", ("defekt", "beschädigt", "bastler", "ersatzteil", "unvollständig",
                   "reparatur", "for parts", "not working", "damaged")),
    ("like_new", ("wie neu", "like new", "sehr gut", "very good", "neuwertig",
                  "kaum getragen", "kaum benutzt")),
    ("new", ("neu mit etikett", "neu ohne etikett", "new with tags",
             "new without tags", "neu/ovp", "originalverpackt", "ungeöffnet",
             "ungetragen", "unbenutzt", "brand new", "nagelneu", "ovp", "neu",
             "new")),
    ("used", ("gebraucht", "getragen", "benutzt", "gut", "good", "akzeptabel",
              "zufriedenstellend", "satisfactory", "used", "pre-owned",
              "second hand")),
)


def normalize_condition(*values: object) -> str:
    """Ordnet Zustandsangaben einem stabilen Code zu; unbekannt bleibt unbekannt."""

    for value in values:
        text = " ".join(str(value or "").split()).casefold()
        if not text:
            continue
        for code, needles in _CONDITION_RULES:
            if any(needle in text for needle in needles):
                return code
    return "unknown"


def normalize_delivery_mode(
    *,
    shipping_available: object = None,
    shipping_cost: object = None,
) -> str:
    """Leitet den Versandmodus aus den bereits normalisierten Versandfeldern ab."""

    if shipping_available is False:
        return "pickup"
    try:
        cost = None if shipping_cost is None else float(shipping_cost)
    except (TypeError, ValueError):
        cost = None
    if cost is not None and cost == 0 and shipping_available is not False:
        return "free"
    if shipping_available is True:
        return "available"
    return "unknown"
