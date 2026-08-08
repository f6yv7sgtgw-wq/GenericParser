"""Vinted search adapter for GenericParser.

The adapter uses Vinted's public web catalog endpoint without account login,
cookie replay, CSRF extraction, proxy rotation, or other protection bypasses.
If Vinted rejects or rate-limits the request, the caller receives a degraded
source status and GenericParser can continue with the other configured source.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

VINTED_BASE = "https://www.vinted.de"
VINTED_CATALOG = f"{VINTED_BASE}/api/v2/catalog/items"
PAGE_SIZE = 96


def _money(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("amount") or value.get("value")
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _photo(item: dict[str, Any]) -> str | None:
    photo = item.get("photo") if isinstance(item.get("photo"), dict) else {}
    return photo.get("url") or photo.get("full_size_url") or photo.get("high_resolution", {}).get("url")


def _location(item: dict[str, Any]) -> str | None:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    return user.get("city") or user.get("country_title") or None


def _condition(item: dict[str, Any]) -> str:
    status = str(item.get("status") or item.get("status_title") or "").casefold()
    if any(term in status for term in ("neu", "new", "ungetragen", "unbenutzt")):
        return "Neu/OVP"
    if any(term in status for term in ("sehr gut", "very good", "wie neu")):
        return "wie neu"
    if any(term in status for term in ("gut", "good", "gebraucht")):
        return "gebraucht"
    return "Zustand offen"


def _normalize(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    item_id = item.get("id")
    title = str(item.get("title") or "").strip()
    if not item_id or not title:
        return None
    url = item.get("url") or f"{VINTED_BASE}/items/{item_id}"
    price = _money(item.get("price") or item.get("total_item_price"))
    return {
        "id": f"vinted:{item_id}",
        "title": title,
        "url": str(url),
        "price": price,
        "price_raw": f"{price:g} €" if price is not None else None,
        "postal_code": None,
        "place": _location(item),
        "posted_at": item.get("created_at_ts") or item.get("created_at") or None,
        "description": None,
        "source_query": query,
        "source": "vinted",
        "source_label": "Vinted",
        "tags": [],
        "image_url": _photo(item),
        "result_info": {
            "offer_type": "Produkt",
            "condition": _condition(item),
            "scope": "Einzelangebot",
            "fit": "prüfen",
            "display_text": f"Vinted · {_condition(item)} · Einzelangebot",
        },
    }


async def search_vinted(query: str, page: int = 0) -> dict[str, Any]:
    params = {
        "search_text": query,
        "page": page + 1,
        "per_page": PAGE_SIZE,
        "order": "newest_first",
    }
    url = f"{VINTED_CATALOG}?{urlencode(params)}"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
        "User-Agent": "GenericParser/1.1 (+https://github.com/f6yv7sgtgw-wq/GenericParser)",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
        if response.status_code in {401, 403, 429}:
            return {
                "listings": [],
                "next_page": None,
                "complete": True,
                "status": "degraded",
                "http_status": response.status_code,
                "reason": "vinted_access_limited",
                "url": url,
            }
        response.raise_for_status()
        data = response.json()
        raw_items = data.get("items") if isinstance(data, dict) else []
        listings = [normalized for raw in (raw_items or []) if (normalized := _normalize(raw, query))]
        complete = len(raw_items or []) < PAGE_SIZE
        return {
            "listings": listings,
            "next_page": None if complete else page + 1,
            "complete": complete,
            "status": "ok",
            "http_status": response.status_code,
            "reason": None,
            "url": url,
        }
    except Exception as exc:
        return {
            "listings": [],
            "next_page": None,
            "complete": True,
            "status": "degraded",
            "http_status": None,
            "reason": f"{type(exc).__name__}: {exc}",
            "url": url,
        }


__all__ = ["search_vinted", "VINTED_BASE", "VINTED_CATALOG"]
