"""Löst Kleinanzeigen-Konvolute in ihre Einzelartikel auf.

Die Trefferliste liefert nur einen gekürzten Teaser. Eine Auflistung der Form
"Zelda 25 €, Mario Kart 20 €" steht ausschließlich in der Detailseite. Dieses
Modul holt die Detailseite nur für Treffer, die die Klassifizierung ohnehin als
Konvolut ausweist, und erzeugt daraus abgeleitete Kacheln.

Abgeleitete Kacheln sind keine eigenständigen Angebote: Sie tragen die URL der
Ursprungsanzeige und verweisen über ``derived_from`` auf sie. Es wird keine URL
erfunden. Schlägt die Auflösung fehl, bleibt es bei der Konvolutkachel.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Awaitable, Callable

from bs4 import BeautifulSoup

DETAIL_BUDGET_PER_PAGE = 3
DETAIL_TIMEOUT_S = 8.0
MIN_ITEMS = 2

# Tausenderpunkte müssen mit erfasst werden, sonst bleibt bei "1.200 €" das
# "1." im Artikelnamen stehen und der Preis wird zu 200.
_PRICE_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{1,6}(?:[.,]\d{1,2})?)\s*(?:€|EUR\b|Euro\b)",
    re.I,
)
_LEADING_NOISE_RE = re.compile(r"^[\s\-–—*•·>+]*(?:\d{1,2}\s*[.)]\s*)?(?:\d{1,2}\s*[xX]\s*)?")
_TRAILING_NOISE_RE = re.compile(r"[\s:\-–—=.,;]+$")
# "Extreme-G 2 je 15 €" meint den Stückpreis; das Füllwort gehört nicht in
# den Artikelnamen.
_TRAILING_FILLER_RE = re.compile(
    # Das führende \s+ ist wesentlich: mit \s* würde "à" das Schluss-a von
    # "Zelda" verschlucken.
    r"\s+(?:je|jeweils|pro\s+st(?:ü|ue)ck|das\s+st(?:ü|ue)ck|st(?:ü|ue)ck|"
    r"pro\s+stk\.?|stk\.?|à)\s*$",
    re.I,
)

# Zeilen, die zwar einen Betrag tragen, aber keinen Artikel bezeichnen. Ohne
# diese Liste würden "Versand 5 €" und "Neupreis 60 €" zu eigenen Kacheln.
_NON_ITEM_SIGNALS = (
    "versand", "porto", "verschick", "gesamt", "zusammen", "insgesamt", "summe",
    "alles", "komplett", "neupreis", "originalpreis", "uvp", "einzeln je",
    "abholung", "selbstabholung", "festpreis", "verhandlungsbasis", "vb",
    "preis pro", "zzgl", "inkl. versand", "paypal", "überweisung",
    "nachlass", "rabatt", "gebot", "tausch",
)


def _clean(value: str) -> str:
    return " ".join(str(value or "").split())


def _price(raw: str) -> float | None:
    """Liest deutsche Beträge; der Punkt ist nur bei drei Folgeziffern ein
    Tausendertrennzeichen, sonst ein Dezimalpunkt."""

    text = raw.strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_bundle_items(description: str) -> list[dict[str, Any]]:
    """Liest Zeilen der Form "<Artikel> <Preis> €" aus einer Beschreibung.

    Gibt eine leere Liste zurück, wenn die Beschreibung keine belastbare
    Auflistung enthält. Genau dann bleibt es bei einer Konvolutkachel.
    """

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in str(description or "").splitlines():
        text = _clean(line)
        if not text or len(text) > 200:
            continue
        lowered = text.casefold()
        if any(signal in lowered for signal in _NON_ITEM_SIGNALS):
            continue
        matches = list(_PRICE_RE.finditer(text))
        # Mehrere Beträge in einer Zeile sind mehrdeutig (Preisspanne,
        # Alt-/Neupreis); nur eine eindeutige Angabe wird ausgewertet.
        if len(matches) != 1:
            continue
        match = matches[0]
        price = _price(match.group(1))
        if price is None or price <= 0:
            continue
        name = text[: match.start()] + text[match.end() :]
        name = _LEADING_NOISE_RE.sub("", _clean(name))
        for _ in range(3):
            stripped = _TRAILING_NOISE_RE.sub("", _TRAILING_FILLER_RE.sub("", name))
            if stripped == name:
                break
            name = stripped
        if len(name) < 3 or len(name) > 120 or not re.search(r"[A-Za-zÄÖÜäöüß]{3}", name):
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append({"title": name, "price": price})
    return items if len(items) >= MIN_ITEMS else []


def _detail_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("#viewad-description-text") or soup.select_one(
        "[class*='viewad-description']"
    )
    if node is None:
        return ""
    return node.get_text("\n", strip=True)


def is_bundle(listing: dict[str, Any]) -> bool:
    classification = listing.get("product_classification")
    classification = classification if isinstance(classification, dict) else {}
    info = listing.get("result_info") if isinstance(listing.get("result_info"), dict) else {}
    scope = str(info.get("scope") or "").casefold()
    return str(classification.get("code") or "") == "bundle" or "konvolut" in scope or "bundle" in scope


def derive_listings(parent: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Baut je Einzelartikel eine Kachel, die auf die Ursprungsanzeige zeigt."""

    parent_id = str(parent.get("id") or "")
    parent_info = parent.get("result_info") if isinstance(parent.get("result_info"), dict) else {}
    derived: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        row = dict(parent)
        row.update(
            {
                "id": f"{parent_id}#item-{index}",
                "title": item["title"],
                "price": item["price"],
                "price_raw": f"{item['price']:g} €",
                "total_price": None,
                "item_price": item["price"],
                # Keine erfundene URL: die Ursprungsanzeige bleibt das Ziel.
                "url": parent.get("url"),
                "description": None,
                "derived": True,
                "derived_from": parent_id,
                "result_info": {
                    **parent_info,
                    "scope": "Einzelangebot",
                    "derived_from_bundle": True,
                },
            }
        )
        derived.append(row)
    return derived


async def resolve_bundles(
    listings: list[dict[str, Any]],
    *,
    fetch_html: Callable[[str], Awaitable[str]],
    budget: int = DETAIL_BUDGET_PER_PAGE,
) -> dict[str, Any]:
    """Ersetzt auflösbare Konvolute durch Einzelkacheln; alles andere bleibt.

    Fail-open: Jeder Fehler beim Abruf oder Parsen lässt die Konvolutkachel
    unverändert stehen.
    """

    candidates = [
        listing
        for listing in listings
        if is_bundle(listing) and str(listing.get("url") or "").startswith("http")
    ][:budget]
    stats = {
        "candidates": len(candidates),
        "budget": budget,
        "resolved": 0,
        "derived": 0,
        "failed": 0,
        "unresolved": 0,
    }
    if not candidates:
        return {"listings": listings, "stats": stats}

    async def load(listing: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        try:
            html = await asyncio.wait_for(
                fetch_html(str(listing.get("url"))), timeout=DETAIL_TIMEOUT_S
            )
            return listing, html
        except Exception:
            return listing, None

    pages = await asyncio.gather(*(load(listing) for listing in candidates))
    replacements: dict[str, list[dict[str, Any]]] = {}
    for listing, html in pages:
        if html is None:
            stats["failed"] += 1
            continue
        try:
            items = parse_bundle_items(_detail_description(html))
        except Exception:
            stats["failed"] += 1
            continue
        if not items:
            stats["unresolved"] += 1
            continue
        derived = derive_listings(listing, items)
        replacements[str(listing.get("id") or "")] = derived
        stats["resolved"] += 1
        stats["derived"] += len(derived)

    if not replacements:
        return {"listings": listings, "stats": stats}

    resolved: list[dict[str, Any]] = []
    for listing in listings:
        replacement = replacements.get(str(listing.get("id") or ""))
        if replacement:
            resolved.extend(replacement)
        else:
            resolved.append(listing)
    return {"listings": resolved, "stats": stats}


__all__ = [
    "DETAIL_BUDGET_PER_PAGE",
    "derive_listings",
    "is_bundle",
    "parse_bundle_items",
    "resolve_bundles",
]
