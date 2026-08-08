"""Vinted adapter for GenericParser.

The primary strategy parses Vinted's public catalog HTML and structured data.
It does not automate login, replay cookies, rotate proxies, or bypass access
controls. The historical JSON catalog endpoint is kept only as a secondary
fallback when it is directly available.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup

VINTED_BASE = "https://www.vinted.de"
VINTED_CATALOG_PAGE = f"{VINTED_BASE}/catalog"
VINTED_CATALOG_API = f"{VINTED_BASE}/api/v2/catalog/items"
PAGE_SIZE = 96
_ITEM_RE = re.compile(r"/items/(\d+)")
_PRICE_RE = re.compile(r"(\d{1,6}(?:[.,]\d{1,2})?)\s*€")


def _money(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("amount") or value.get("value") or value.get("price")
    try:
        return float(str(value).replace("€", "").replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _condition_text(value: Any) -> str:
    status = str(value or "").casefold()
    if any(term in status for term in ("neu", "new", "ungetragen", "unbenutzt")):
        return "Neu/OVP"
    if any(term in status for term in ("sehr gut", "very good", "wie neu")):
        return "wie neu"
    if any(term in status for term in ("gut", "good", "gebraucht")):
        return "gebraucht"
    return "Zustand offen"


def _listing(item_id: str, title: str, url: str, query: str, *, price: float | None = None,
             image_url: str | None = None, place: str | None = None,
             condition: str = "Zustand offen") -> dict[str, Any]:
    return {
        "id": f"vinted:{item_id}",
        "title": title.strip(),
        "url": urljoin(VINTED_BASE, url),
        "price": price,
        "price_raw": f"{price:g} €" if price is not None else None,
        "postal_code": None,
        "place": place,
        "posted_at": None,
        "description": None,
        "source_query": query,
        "source": "vinted",
        "source_label": "Vinted",
        "tags": [],
        "image_url": image_url,
        "result_info": {
            "offer_type": "Produkt",
            "condition": condition,
            "scope": "Einzelangebot",
            "fit": "prüfen",
            "display_text": f"Vinted · {condition} · Einzelangebot",
        },
    }


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _from_structured_data(soup: BeautifulSoup, query: str) -> list[dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text() or "null")
        except (TypeError, json.JSONDecodeError):
            continue
        for obj in _walk_json(data):
            obj_type = str(obj.get("@type") or "").casefold()
            url = str(obj.get("url") or "")
            match = _ITEM_RE.search(url)
            if not match or obj_type not in {"product", "listitem", "thing"}:
                continue
            item_id = match.group(1)
            title = str(obj.get("name") or obj.get("title") or "").strip()
            if not title:
                continue
            offers = obj.get("offers") if isinstance(obj.get("offers"), dict) else {}
            price = _money(offers.get("price") or obj.get("price"))
            image = obj.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")
            condition = _condition_text(obj.get("itemCondition") or obj.get("condition"))
            results[item_id] = _listing(item_id, title, url, query, price=price, image_url=str(image) if image else None, condition=condition)
    return list(results.values())


def _from_cards(soup: BeautifulSoup, query: str) -> list[dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for anchor in soup.find_all("a", href=_ITEM_RE):
        href = str(anchor.get("href") or "")
        match = _ITEM_RE.search(href)
        if not match:
            continue
        item_id = match.group(1)
        container = anchor.find_parent(["article", "li"])
        if container is None:
            container = anchor.find_parent("div") or anchor
        image = container.find("img") if hasattr(container, "find") else None
        title = str(anchor.get("title") or anchor.get("aria-label") or "").strip()
        if not title and image is not None:
            title = str(image.get("alt") or "").strip()
        text = " ".join(container.stripped_strings) if hasattr(container, "stripped_strings") else ""
        if not title:
            title = text[:180].strip()
        if not title:
            continue
        price_match = _PRICE_RE.search(text)
        price = _money(price_match.group(1)) if price_match else None
        image_url = None
        if image is not None:
            image_url = image.get("src") or image.get("data-src") or image.get("data-testid-src")
        condition = _condition_text(text)
        results[item_id] = _listing(item_id, title, href, query, price=price, image_url=urljoin(VINTED_BASE, str(image_url)) if image_url else None, condition=condition)
    return list(results.values())


def _normalize_api(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    item_id = item.get("id")
    title = str(item.get("title") or "").strip()
    if not item_id or not title:
        return None
    photo = item.get("photo") if isinstance(item.get("photo"), dict) else {}
    image = photo.get("url") or photo.get("full_size_url")
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    return _listing(
        str(item_id), title, str(item.get("url") or f"/items/{item_id}"), query,
        price=_money(item.get("price") or item.get("total_item_price")),
        image_url=image,
        place=user.get("city") or user.get("country_title"),
        condition=_condition_text(item.get("status") or item.get("status_title")),
    )


async def _fetch_html(client: httpx.AsyncClient, query: str, page: int) -> dict[str, Any]:
    params = {"search_text": query, "order": "newest_first", "page": page + 1}
    url = f"{VINTED_CATALOG_PAGE}?{urlencode(params)}"
    response = await client.get(url, headers={"Accept": "text/html,application/xhtml+xml"})
    if response.status_code in {401, 403, 429}:
        return {"listings": [], "status": "degraded", "http_status": response.status_code, "reason": "vinted_html_access_limited", "url": url, "strategy": "html"}
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    structured = _from_structured_data(soup, query)
    cards = _from_cards(soup, query)
    merged = {item["id"]: item for item in structured}
    merged.update({item["id"]: item for item in cards})
    listings = list(merged.values())
    if not listings:
        return {"listings": [], "status": "degraded", "http_status": response.status_code, "reason": "vinted_html_no_items_parsed", "url": url, "strategy": "html"}
    return {"listings": listings, "status": "ok", "http_status": response.status_code, "reason": None, "url": url, "strategy": "html"}


async def _fetch_api(client: httpx.AsyncClient, query: str, page: int) -> dict[str, Any]:
    params = {"search_text": query, "page": page + 1, "per_page": PAGE_SIZE, "order": "newest_first"}
    url = f"{VINTED_CATALOG_API}?{urlencode(params)}"
    response = await client.get(url, headers={"Accept": "application/json"})
    if response.status_code in {401, 403, 429}:
        return {"listings": [], "status": "degraded", "http_status": response.status_code, "reason": "vinted_api_access_limited", "url": url, "strategy": "api"}
    response.raise_for_status()
    data = response.json()
    raw = data.get("items") if isinstance(data, dict) else []
    listings = [item for value in (raw or []) if (item := _normalize_api(value, query))]
    return {"listings": listings, "status": "ok" if listings else "degraded", "http_status": response.status_code, "reason": None if listings else "vinted_api_no_items", "url": url, "strategy": "api"}


async def search_vinted(query: str, page: int = 0) -> dict[str, Any]:
    headers = {
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (compatible; GenericParser/1.1; +https://github.com/f6yv7sgtgw-wq/GenericParser)",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            html = await _fetch_html(client, query, page)
            if html.get("listings"):
                count = len(html["listings"])
                html["complete"] = count < 20
                html["next_page"] = None if html["complete"] else page + 1
                return html
            api = await _fetch_api(client, query, page)
            if api.get("listings"):
                count = len(api["listings"])
                api["complete"] = count < PAGE_SIZE
                api["next_page"] = None if api["complete"] else page + 1
                api["reason"] = f"html:{html.get('reason')}; api_fallback_ok"
                return api
            return {
                "listings": [], "next_page": None, "complete": True,
                "status": "degraded", "http_status": api.get("http_status") or html.get("http_status"),
                "reason": f"html:{html.get('reason')}; api:{api.get('reason')}",
                "url": html.get("url"), "strategy": "html+api-fallback",
            }
    except Exception as exc:
        return {
            "listings": [], "next_page": None, "complete": True,
            "status": "degraded", "http_status": None,
            "reason": f"{type(exc).__name__}: {exc}",
            "url": f"{VINTED_CATALOG_PAGE}?{urlencode({'search_text': query, 'page': page + 1})}",
            "strategy": "html+api-fallback",
        }


__all__ = ["search_vinted", "VINTED_BASE", "VINTED_CATALOG_PAGE", "VINTED_CATALOG_API"]
