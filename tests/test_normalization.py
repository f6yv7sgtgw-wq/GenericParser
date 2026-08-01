from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from generic_parser import (
    PriceFlag,
    compact_text,
    normalize_text,
    parse_location,
    parse_posted_at,
    parse_price,
)

BERLIN = ZoneInfo("Europe/Berlin")


def test_normalize_text_and_compact_model_number() -> None:
    assert normalize_text("  XY-500 / Größe Ä  ") == "xy 500 groesse ae"
    assert compact_text("XY-500") == "xy500"
    assert compact_text("XY 500") == "xy500"


@pytest.mark.parametrize(
    ("raw", "amount", "flags"),
    [
        ("120 €", Decimal("120"), frozenset()),
        ("120 € VB", Decimal("120"), frozenset({PriceFlag.NEGOTIABLE})),
        ("1.250 €", Decimal("1250"), frozenset()),
        ("1.250,50 €", Decimal("1250.50"), frozenset()),
        ("Zu verschenken", Decimal("0"), frozenset({PriceFlag.FREE})),
        ("VB", None, frozenset({PriceFlag.NEGOTIABLE, PriceFlag.UNKNOWN})),
        ("", None, frozenset({PriceFlag.UNKNOWN})),
        ("1 €", Decimal("1"), frozenset({PriceFlag.SUSPICIOUS_LOW})),
    ],
)
def test_parse_price(raw: str, amount: Decimal | None, flags: frozenset[PriceFlag]) -> None:
    result = parse_price(raw)
    assert result.amount == amount
    assert result.flags == flags


def test_zero_and_unknown_price_remain_distinct() -> None:
    assert parse_price("Zu verschenken").amount == Decimal("0")
    assert parse_price("").amount is None


def test_parse_location_with_distance() -> None:
    result = parse_location("12345 Musterstadt (12,5 km)")
    assert result.postal_code == "12345"
    assert result.place == "Musterstadt"
    assert result.distance_km == Decimal("12.5")


def test_parse_location_without_distance() -> None:
    result = parse_location("12345 Musterstadt")
    assert result.postal_code == "12345"
    assert result.place == "Musterstadt"
    assert result.distance_km is None


def test_parse_relative_dates_in_berlin_timezone() -> None:
    now = datetime(2026, 8, 1, 8, 49, tzinfo=BERLIN)
    assert parse_posted_at("Heute, 07:15", now=now) == datetime(
        2026, 8, 1, 7, 15, tzinfo=BERLIN
    )
    assert parse_posted_at("Gestern, 23:10", now=now) == datetime(
        2026, 7, 31, 23, 10, tzinfo=BERLIN
    )


def test_parse_absolute_date() -> None:
    assert parse_posted_at("27.07.2026") == datetime(
        2026, 7, 27, 0, 0, tzinfo=BERLIN
    )


def test_unknown_date_format_is_explicit_error() -> None:
    with pytest.raises(ValueError, match="Unbekanntes Datumsformat"):
        parse_posted_at("vor wenigen Minuten")
