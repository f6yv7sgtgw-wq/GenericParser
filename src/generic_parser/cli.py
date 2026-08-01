from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from .config import ConfigurationError, load_profile
from .models import Listing
from .service import GenericParser
from .sources.kleinanzeigen import (
    FetchedPage,
    KleinanzeigenAdapter,
    KleinanzeigenError,
    KleinanzeigenHttpClient,
    KleinanzeigenPageParser,
    extract_location_id,
)


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def listing_to_dict(listing: Listing) -> dict[str, object]:
    return {
        "id": listing.id,
        "title": listing.title,
        "url": listing.url,
        "price": _decimal(listing.price.amount),
        "price_raw": listing.price.raw,
        "price_flags": sorted(flag.value for flag in listing.price.flags),
        "postal_code": listing.location.postal_code,
        "place": listing.location.place,
        "distance_km": _decimal(listing.location.distance_km),
        "posted_at": listing.posted_at.isoformat() if listing.posted_at else None,
        "description": listing.description,
        "source_query": listing.source_query,
        "tags": list(listing.tags),
        "image_url": listing.image_url,
    }


def _print_listings(listings: Sequence[Listing], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps([listing_to_dict(item) for item in listings], ensure_ascii=False, indent=2))
        return
    if not listings:
        print("Keine Anzeigen gefunden.")
        return
    for item in listings:
        price = f"{item.price.amount} €" if item.price.amount is not None else item.price.raw or "Preis unbekannt"
        location = " ".join(part for part in (item.location.postal_code, item.location.place) if part)
        print(f"{item.title} · {price} · {location}")
        print(item.url)


def _fetch(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    with KleinanzeigenHttpClient() as http:
        adapter = KleinanzeigenAdapter(http=http)
        listings = GenericParser(adapter).search(profile)
        _print_listings(listings[: args.limit] if args.limit else listings, json_output=args.json)
        if not args.json:
            for diagnostic in adapter.last_diagnostics:
                print(
                    f"[{diagnostic.state.value}] Karten: {diagnostic.cards_found}, "
                    f"Listings: {diagnostic.listings_parsed}, "
                    f"Duplikate: {diagnostic.duplicates_skipped}, "
                    f"Kartenfehler: {len(diagnostic.errors)}"
                )
    return 0


def _fixture(args: argparse.Namespace) -> int:
    source = Path(args.html)
    html = source.read_text(encoding="utf-8")
    uri = source.resolve().as_uri()
    page = FetchedPage(uri, uri, 200, html)
    parsed = KleinanzeigenPageParser().parse(page, source_query=args.query)
    _print_listings(parsed.listings, json_output=args.json)
    if not args.json:
        print(asdict(parsed.diagnostics))
    return 0


def _location_id(args: argparse.Namespace) -> int:
    location_id = extract_location_id(args.url)
    if location_id is None:
        print("Keine Location-ID in der URL gefunden.", file=sys.stderr)
        return 2
    print(location_id)
    return 0


def _verify_location(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    with KleinanzeigenHttpClient() as http:
        adapter = KleinanzeigenAdapter(http=http)
        result = adapter.verify_location_id(profile, query=args.query, test_radius_km=args.radius)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.radius_effective else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="generic-parser")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Echte Kleinanzeigen-Suche ausführen")
    fetch.add_argument("profile", type=Path)
    fetch.add_argument("--limit", type=int, default=0)
    fetch.add_argument("--json", action="store_true")
    fetch.set_defaults(handler=_fetch)

    fixture = sub.add_parser("parse-fixture", help="Gespeicherte HTML-Seite parsen")
    fixture.add_argument("html", type=Path)
    fixture.add_argument("--query", default="fixture")
    fixture.add_argument("--json", action="store_true")
    fixture.set_defaults(handler=_fixture)

    location = sub.add_parser("location-id", help="Location-ID aus Such-URL lesen")
    location.add_argument("url")
    location.set_defaults(handler=_location_id)

    verify = sub.add_parser("verify-location", help="Radiuswirkung einer Location-ID prüfen")
    verify.add_argument("profile", type=Path)
    verify.add_argument("--query")
    verify.add_argument("--radius", type=int, default=5)
    verify.set_defaults(handler=_verify_location)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (ConfigurationError, KleinanzeigenError, OSError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
