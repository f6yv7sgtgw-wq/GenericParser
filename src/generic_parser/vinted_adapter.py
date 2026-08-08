"""Vinted adapter for GenericParser.

Production strategy: use the isolated Cloudflare Browser Run worker that has
already proven public Vinted catalog access. If that component is unavailable,
fall back to the ordinary anonymous public-web session HTML/API strategy.
No login, stored user cookies, proxy rotation, challenge solving or access-
control bypass is used. Vinted remains fail-open so Kleinanzeigen continues.
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
VINTED_BROWSER_WORKER = "https://genericparser-vinted-poc.f6yv7sgtgw.workers.dev"
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
        "url": urljoin(VINTED_BASE, url) if url else None,
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
            if isinstance(image, list): image = image[0] if image else None
            if isinstance(image, dict): image = image.get("url")
            results[item_id] = _listing(item_id, title, url, query, price=price,
                                        image_url=str(image) if image else None,
                                        condition=_condition_text(obj.get("itemCondition") or obj.get("condition")))
    return list(results.values())


def _from_cards(soup: BeautifulSoup, query: str) -> list[dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for anchor in soup.find_all("a", href=_ITEM_RE):
        href = str(anchor.get("href") or "")
        match = _ITEM_RE.search(href)
        if not match: continue
        item_id = match.group(1)
        container = anchor.find_parent(["article", "li"]) or anchor.find_parent("div") or anchor
        image = container.find("img") if hasattr(container, "find") else None
        title = str(anchor.get("title") or anchor.get("aria-label") or "").strip()
        if not title and image is not None: title = str(image.get("alt") or "").strip()
        text = " ".join(container.stripped_strings) if hasattr(container, "stripped_strings") else ""
        if not title: title = text[:180].strip()
        if not title: continue
        price_match = _PRICE_RE.search(text)
        image_url = None if image is None else image.get("src") or image.get("data-src") or image.get("data-testid-src")
        results[item_id] = _listing(item_id, title, href, query,
                                    price=_money(price_match.group(1)) if price_match else None,
                                    image_url=urljoin(VINTED_BASE, str(image_url)) if image_url else None,
                                    condition=_condition_text(text))
    return list(results.values())


def _normalize_api(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    item_id = item.get("id")
    title = str(item.get("title") or "").strip()
    if not item_id or not title: return None
    photo = item.get("photo") if isinstance(item.get("photo"), dict) else {}
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    return _listing(str(item_id), title, str(item.get("url") or f"/items/{item_id}"), query,
                    price=_money(item.get("price") or item.get("total_item_price")),
                    image_url=photo.get("url") or photo.get("full_size_url"),
                    place=user.get("city") or user.get("country_title"),
                    condition=_condition_text(item.get("status") or item.get("status_title")))


def _normalize_browser_item(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    raw_id = str(item.get("id") or "").removeprefix("vinted:")
    title = str(item.get("title") or "").strip()
    if not raw_id or not title: return None
    return _listing(raw_id, title, str(item.get("url") or ""), query,
                    price=_money(item.get("price")),
                    image_url=item.get("image_url"),
                    condition=_condition_text(item.get("condition")))


async def _fetch_browser_worker(query: str, page: int) -> dict[str, Any]:
    """Call the deployed Browser Run component through its stable component contract."""
    params = {"q": query, "page": max(0, int(page))}
    url = f"{VINTED_BROWSER_WORKER}/search?{urlencode(params)}"
    try:
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
        data = response.json() if response.content else {}
        if response.status_code != 200 or data.get("status") != "ok":
            return {"listings": [], "status": "degraded", "http_status": response.status_code,
                    "reason": data.get("reason") or "vinted_browser_worker_unavailable",
                    "url": url, "strategy": "browser-run-worker", "browser": data.get("browser")}
        listings = [row for raw in (data.get("listings") or []) if (row := _normalize_browser_item(raw, query))]
        return {
            "listings": listings,
            "status": "ok" if listings else "degraded",
            "http_status": response.status_code,
            "reason": None if listings else "vinted_browser_worker_no_items",
            "url": data.get("targetUrl") or url,
            "strategy": "browser-run-worker",
            "browser": data.get("browser"),
            "component": data.get("component"),
            "revision": data.get("revision"),
            "complete": len(listings) < 25,
            "next_page": None if len(listings) < 25 else page + 1,
        }
    except Exception as exc:
        return {"listings": [], "status": "degraded", "http_status": None,
                "reason": f"browser-worker:{type(exc).__name__}: {exc}",
                "url": url, "strategy": "browser-run-worker"}


async def _bootstrap_session(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get(f"{VINTED_BASE}/", headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Cache-Control": "no-cache"})
    cookie_count = len(client.cookies)
    if response.status_code in {401, 403, 429}:
        return {"status": "degraded", "http_status": response.status_code, "reason": "vinted_session_bootstrap_access_limited", "cookie_count": cookie_count}
    response.raise_for_status()
    return {"status": "ok", "http_status": response.status_code, "reason": None, "cookie_count": cookie_count}


async def _fetch_html(client: httpx.AsyncClient, query: str, page: int) -> dict[str, Any]:
    params = {"search_text": query, "order": "newest_first", "page": page + 1}
    url = f"{VINTED_CATALOG_PAGE}?{urlencode(params)}"
    response = await client.get(url, headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Referer": f"{VINTED_BASE}/"})
    if response.status_code in {401, 403, 429}:
        return {"listings": [], "status": "degraded", "http_status": response.status_code, "reason": "vinted_html_access_limited", "url": url, "strategy": "session+html"}
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    merged = {item["id"]: item for item in _from_structured_data(soup, query)}
    merged.update({item["id"]: item for item in _from_cards(soup, query)})
    listings = list(merged.values())
    return {"listings": listings, "status": "ok" if listings else "degraded", "http_status": response.status_code,
            "reason": None if listings else "vinted_html_no_items_parsed", "url": url, "strategy": "session+html"}


async def _fetch_api(client: httpx.AsyncClient, query: str, page: int) -> dict[str, Any]:
    params = {"search_text": query, "page": page + 1, "per_page": PAGE_SIZE, "order": "newest_first"}
    url = f"{VINTED_CATALOG_API}?{urlencode(params)}"
    response = await client.get(url, headers={"Accept": "application/json", "Referer": f"{VINTED_CATALOG_PAGE}?{urlencode({'search_text': query})}"})
    if response.status_code in {401, 403, 429}:
        return {"listings": [], "status": "degraded", "http_status": response.status_code, "reason": "vinted_api_access_limited", "url": url, "strategy": "session+api"}
    response.raise_for_status()
    data = response.json()
    raw = data.get("items") if isinstance(data, dict) else []
    listings = [item for value in (raw or []) if (item := _normalize_api(value, query))]
    return {"listings": listings, "status": "ok" if listings else "degraded", "http_status": response.status_code,
            "reason": None if listings else "vinted_api_no_items", "url": url, "strategy": "session+api"}


async def search_vinted(query: str, page: int = 0) -> dict[str, Any]:
    browser = await _fetch_browser_worker(query, page)
    if browser.get("listings"):
        return browser

    headers = {
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (compatible; GenericParser; +https://github.com/f6yv7sgtgw-wq/GenericParser)",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            bootstrap = await _bootstrap_session(client)
            html = await _fetch_html(client, query, page)
            html["bootstrap"] = bootstrap
            html["browser_fallback"] = browser
            if html.get("listings"):
                count = len(html["listings"]); html["complete"] = count < 20; html["next_page"] = None if html["complete"] else page + 1
                html["strategy"] = "browser-run-worker-fallback+session+html"
                return html
            api = await _fetch_api(client, query, page)
            api["bootstrap"] = bootstrap; api["browser_fallback"] = browser
            if api.get("listings"):
                count = len(api["listings"]); api["complete"] = count < PAGE_SIZE; api["next_page"] = None if api["complete"] else page + 1
                api["strategy"] = "browser-run-worker-fallback+session+api"
                return api
            return {"listings": [], "next_page": None, "complete": True, "status": "degraded",
                    "http_status": api.get("http_status") or html.get("http_status") or browser.get("http_status"),
                    "reason": f"browser:{browser.get('reason')}; bootstrap:{bootstrap.get('reason')}; html:{html.get('reason')}; api:{api.get('reason')}",
                    "url": browser.get("url") or html.get("url"), "strategy": "browser-run-worker+public-web-fallback",
                    "bootstrap": bootstrap, "browser_fallback": browser}
    except Exception as exc:
        return {"listings": [], "next_page": None, "complete": True, "status": "degraded", "http_status": browser.get("http_status"),
                "reason": f"browser:{browser.get('reason')}; fallback:{type(exc).__name__}: {exc}",
                "url": browser.get("url"), "strategy": "browser-run-worker+public-web-fallback"}


__all__ = ["search_vinted", "VINTED_BASE", "VINTED_CATALOG_PAGE", "VINTED_CATALOG_API", "VINTED_BROWSER_WORKER", "_bootstrap_session", "_fetch_browser_worker"]
