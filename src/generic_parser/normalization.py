from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from .models import Location, NormalizedPrice, PriceFlag

BERLIN = ZoneInfo("Europe/Berlin")
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
    """Wandelt Kleinanzeigen-Zeitangaben in Europe/Berlin in absolute Zeiten um."""

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
