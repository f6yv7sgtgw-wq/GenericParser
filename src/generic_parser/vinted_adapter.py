"""Vinted adapter for GenericParser.

Production strategy: use a request-scoped Cloudflare Service Binding to the
isolated Browser Run Worker. The working catalog search path remains unchanged;
1.3 adds fail-open detail enrichment behind it. If the binding is unavailable
or fails, fall back to the ordinary anonymous public-web session HTML/API
strategy. No public workers.dev URL is a production dependency.
"""
from __future__ import annotations

import json
import re
from contextvars import ContextVar
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

VINTED_BASE = "https://www.vinted.de"
VINTED_CATALOG_PAGE = f"{VINTED_BASE}/catalog"
VINTED_CATALOG_API = f"{VINTED_BASE}/api/v2/catalog/items"
VINTED_BROWSER_ORIGIN = "https://vinted-browser.internal"
PAGE_SIZE = 96
DETAIL_BATCH_LIMIT = 3
_ITEM_RE = re.compile(r"/items/(\d+)")
_PRICE_RE = re.compile(r"(\d{1,6}(?:[.,]\d{1,2})?)\s*€")
_VINTED_BROWSER_BINDING: ContextVar[Any | None] = ContextVar("vinted_browser_binding", default=None)


def set_vinted_browser_binding(binding: Any | None):
    return _VINTED_BROWSER_BINDING.set(binding)


def reset_vinted_browser_binding(token) -> None:
    _VINTED_BROWSER_BINDING.reset(token)


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


def _listing(
    item_id: str,
    title: str,
    url: str,
    query: str,
    *,
    price: float | None = None,
    image_url: str | None = None,
    place: str | None = None,
    condition: str = "Zustand offen",
    description: str | None = None,
    detail_status: str | None = None,
    detail_fields: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"vinted:{item_id}",
        "title": title.strip(),
        "url": urljoin(VINTED_BASE, url) if url else None,
        "price": price,
        "price_raw": f"{price:g} €" if price is not None else None,
        "postal_code": None,
        "place": place,
        "posted_at": None,
        "description": description,
        "source_query": query,
        "source": "vinted",
        "source_label": "Vinted",
        "tags": [],
        "image_url": image_url,
        "detail_enrichment": {
            "status": detail_status or "not_requested",
            "fields": list(detail_fields or []),
        },
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
    results = {}
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text() or "null")
        except (TypeError, json.JSONDecodeError):
            continue
        for obj in _walk_json(data):
            url = str(obj.get("url") or "")
            match = _ITEM_RE.search(url)
            if not match or str(obj.get("@type") or "").casefold() not in {"product", "listitem", "thing"}:
                continue
            title = str(obj.get("name") or obj.get("title") or "").strip()
            if not title:
                continue
            offers = obj.get("offers") if isinstance(obj.get("offers"), dict) else {}
            image = obj.get("image")
            image = image[0] if isinstance(image, list) and image else image
            image = image.get("url") if isinstance(image, dict) else image
            results[match.group(1)] = _listing(
                match.group(1), title, url, query,
                price=_money(offers.get("price") or obj.get("price")),
                image_url=str(image) if image else None,
                condition=_condition_text(obj.get("itemCondition") or obj.get("condition")),
                description=str(obj.get("description") or "").strip() or None,
            )
    return list(results.values())


def _from_cards(soup: BeautifulSoup, query: str) -> list[dict[str, Any]]:
    results = {}
    for anchor in soup.find_all("a", href=_ITEM_RE):
        href = str(anchor.get("href") or "")
        match = _ITEM_RE.search(href)
        if not match:
            continue
        container = anchor.find_parent(["article", "li"]) or anchor.find_parent("div") or anchor
        image = container.find("img") if hasattr(container, "find") else None
        title = str(anchor.get("title") or anchor.get("aria-label") or "").strip() or (str(image.get("alt") or "").strip() if image else "")
        text = " ".join(container.stripped_strings) if hasattr(container, "stripped_strings") else ""
        title = title or text[:180].strip()
        if not title:
            continue
        pm = _PRICE_RE.search(text)
        image_url = None if image is None else image.get("src") or image.get("data-src") or image.get("data-testid-src")
        results[match.group(1)] = _listing(
            match.group(1), title, href, query,
            price=_money(pm.group(1)) if pm else None,
            image_url=urljoin(VINTED_BASE, str(image_url)) if image_url else None,
            condition=_condition_text(text),
        )
    return list(results.values())


def _normalize_api(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    item_id = item.get("id")
    title = str(item.get("title") or "").strip()
    if not item_id or not title:
        return None
    photo = item.get("photo") if isinstance(item.get("photo"), dict) else {}
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    return _listing(
        str(item_id), title, str(item.get("url") or f"/items/{item_id}"), query,
        price=_money(item.get("price") or item.get("total_item_price")),
        image_url=photo.get("url") or photo.get("full_size_url"),
        place=user.get("city") or user.get("country_title"),
        condition=_condition_text(item.get("status") or item.get("status_title")),
        description=str(item.get("description") or "").strip() or None,
    )


def _normalize_browser_item(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    raw_id = str(item.get("id") or "").removeprefix("vinted:")
    title = str(item.get("title") or "").strip()
    if not raw_id or not title:
        return None
    fields = item.get("detail_fields") if isinstance(item.get("detail_fields"), list) else []
    return _listing(
        raw_id,
        title,
        str(item.get("url") or ""),
        query,
        price=_money(item.get("price")),
        image_url=item.get("image_url"),
        place=item.get("place"),
        condition=_condition_text(item.get("condition")),
        description=str(item.get("description") or "").strip() or None,
        detail_status=str(item.get("detail_status") or "not_requested"),
        detail_fields=[str(value) for value in fields],
    )


async def _binding_json_response(binding: Any, url: str) -> tuple[int, dict[str, Any]]:
    response = await binding.fetch(url)
    status = int(getattr(response, "status", 0) or 0)
    text = await response.text()
    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError:
        return status, {"status": "error", "reason": "vinted_service_binding_non_json"}
    return status, data


async def _fetch_browser_worker(query: str, page: int) -> dict[str, Any]:
    params = {"q": query, "page": max(0, int(page))}
    url = f"{VINTED_BROWSER_ORIGIN}/search?{urlencode(params)}"
    binding = _VINTED_BROWSER_BINDING.get()
    if binding is None:
        return {"listings": [], "status": "degraded", "http_status": None, "reason": "vinted_service_binding_unavailable", "url": url, "strategy": "service-binding"}
    try:
        status, data = await _binding_json_response(binding, url)
        if status != 200 or data.get("status") != "ok":
            return {"listings": [], "status": "degraded", "http_status": status, "reason": data.get("reason") or "vinted_service_binding_unavailable", "url": url, "strategy": "service-binding", "browser": data.get("browser")}
        listings = [row for raw in (data.get("listings") or []) if (row := _normalize_browser_item(raw, query))]
        enrichment = data.get("enrichment") if isinstance(data.get("enrichment"), dict) else {}
        return {
            "listings": listings,
            "status": "ok" if listings else "degraded",
            "http_status": status,
            "reason": None if listings else "vinted_service_binding_no_items",
            "url": data.get("targetUrl") or url,
            "strategy": "service-binding",
            "browser": data.get("browser"),
            "component": data.get("component"),
            "revision": data.get("revision"),
            "enrichment": enrichment,
            "complete": bool(data.get("complete", len(listings) < 25)),
            "next_page": data.get("nextPage", None if len(listings) < 25 else page + 1),
        }
    except Exception as exc:
        return {"listings": [], "status": "degraded", "http_status": None, "reason": f"service-binding:{type(exc).__name__}: {exc}", "url": url, "strategy": "service-binding"}


def _validated_detail_rows(listings: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    if not listings:
        raise ValueError("at least one Vinted listing is required")
    if len(listings) > DETAIL_BATCH_LIMIT:
        raise ValueError(f"Vinted detail batch exceeds limit {DETAIL_BATCH_LIMIT}")

    validated: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = set()
    for listing in listings:
        if not isinstance(listing, dict):
            raise ValueError("Vinted detail rows must be objects")
        listing_id = str(listing.get("id") or "")
        url = str(listing.get("url") or "")
        parsed = urlparse(url)
        match = re.fullmatch(r"/items/(\d+)(?:-[^/?#]+)?/?", parsed.path)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").casefold() not in {"vinted.de", "www.vinted.de"}
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not match
        ):
            raise ValueError("only canonical https://www.vinted.de/items/... URLs may be enriched")
        canonical_id = f"vinted:{match.group(1)}"
        if listing_id != canonical_id:
            raise ValueError("Vinted listing id does not match its item URL")
        if canonical_id in seen:
            continue
        seen.add(canonical_id)
        validated.append((listing, f"{VINTED_BASE}{parsed.path}"))
    if not validated:
        raise ValueError("Vinted detail batch contains no unique listings")
    return validated


async def enrich_vinted_details(listings: list[dict[str, Any]]) -> dict[str, Any]:
    """Load one fail-open background batch through the private service binding.

    The Browser Run component accepts at most three canonical Vinted item URLs.
    It opens those three detail pages in parallel, while callers serialize the
    batches so catalog pagination never waits for the remaining detail work.
    """

    validated = _validated_detail_rows(listings)
    binding = _VINTED_BROWSER_BINDING.get()
    params = urlencode([("item", url) for _, url in validated])
    url = f"{VINTED_BROWSER_ORIGIN}/enrich?{params}"
    if binding is None:
        return {
            "listings": [],
            "status": "degraded",
            "http_status": None,
            "reason": "vinted_service_binding_unavailable",
            "url": url,
            "strategy": "service-binding-deferred-detail",
        }
    try:
        status, data = await _binding_json_response(binding, url)
        if status != 200 or data.get("status") != "ok":
            return {
                "listings": [],
                "status": "degraded",
                "http_status": status,
                "reason": data.get("reason") or "vinted_deferred_detail_unavailable",
                "url": url,
                "strategy": "service-binding-deferred-detail",
                "enrichment": data.get("enrichment"),
            }
        originals = {str(item.get("id")): item for item, _ in validated}
        normalized = []
        for raw in data.get("listings") or []:
            raw_id = str(raw.get("id") or "") if isinstance(raw, dict) else ""
            original = originals.get(raw_id) or {}
            query = str(original.get("source_query") or "")
            item = _normalize_browser_item(raw, query) if isinstance(raw, dict) else None
            if item is not None:
                normalized.append(item)
        return {
            "listings": normalized,
            "status": "ok" if normalized else "degraded",
            "http_status": status,
            "reason": None if normalized else "vinted_deferred_detail_no_items",
            "url": url,
            "strategy": "service-binding-deferred-detail",
            "component": data.get("component"),
            "revision": data.get("revision"),
            "elapsed_ms": data.get("elapsedMs"),
            "enrichment": data.get("enrichment") if isinstance(data.get("enrichment"), dict) else {},
        }
    except Exception as exc:
        return {
            "listings": [],
            "status": "degraded",
            "http_status": None,
            "reason": f"service-binding:{type(exc).__name__}: {exc}",
            "url": url,
            "strategy": "service-binding-deferred-detail",
        }


async def _bootstrap_session(client):
    response = await client.get(f"{VINTED_BASE}/", headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Cache-Control": "no-cache"})
    cookie_count = len(client.cookies)
    if response.status_code in {401, 403, 429}:
        return {"status": "degraded", "http_status": response.status_code, "reason": "vinted_session_bootstrap_access_limited", "cookie_count": cookie_count}
    response.raise_for_status()
    return {"status": "ok", "http_status": response.status_code, "reason": None, "cookie_count": cookie_count}


async def _fetch_html(client, query, page):
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
    return {"listings": listings, "status": "ok" if listings else "degraded", "http_status": response.status_code, "reason": None if listings else "vinted_html_no_items_parsed", "url": url, "strategy": "session+html"}


async def _fetch_api(client, query, page):
    params = {"search_text": query, "page": page + 1, "per_page": PAGE_SIZE, "order": "newest_first"}
    url = f"{VINTED_CATALOG_API}?{urlencode(params)}"
    response = await client.get(url, headers={"Accept": "application/json", "Referer": f"{VINTED_CATALOG_PAGE}?{urlencode({'search_text': query})}"})
    if response.status_code in {401, 403, 429}:
        return {"listings": [], "status": "degraded", "http_status": response.status_code, "reason": "vinted_api_access_limited", "url": url, "strategy": "session+api"}
    response.raise_for_status()
    data = response.json()
    raw = data.get("items") if isinstance(data, dict) else []
    listings = [item for value in (raw or []) if (item := _normalize_api(value, query))]
    return {"listings": listings, "status": "ok" if listings else "degraded", "http_status": response.status_code, "reason": None if listings else "vinted_api_no_items", "url": url, "strategy": "session+api"}


async def search_vinted(query: str, page: int = 0) -> dict[str, Any]:
    browser = await _fetch_browser_worker(query, page)
    if browser.get("listings"):
        return browser
    headers = {"Accept-Language": "de-DE,de;q=0.9,en;q=0.7", "User-Agent": "Mozilla/5.0 (compatible; GenericParser; +https://github.com/f6yv7sgtgw-wq/GenericParser)"}
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers, trust_env=False) as client:
            bootstrap = await _bootstrap_session(client)
            html = await _fetch_html(client, query, page)
            html["bootstrap"] = bootstrap
            html["browser_fallback"] = browser
            if html.get("listings"):
                count = len(html["listings"])
                html["complete"] = count < 20
                html["next_page"] = None if html["complete"] else page + 1
                html["strategy"] = "service-binding-fallback+session+html"
                return html
            api = await _fetch_api(client, query, page)
            api["bootstrap"] = bootstrap
            api["browser_fallback"] = browser
            if api.get("listings"):
                count = len(api["listings"])
                api["complete"] = count < PAGE_SIZE
                api["next_page"] = None if api["complete"] else page + 1
                api["strategy"] = "service-binding-fallback+session+api"
                return api
            return {"listings": [], "next_page": None, "complete": True, "status": "degraded", "http_status": api.get("http_status") or html.get("http_status") or browser.get("http_status"), "reason": f"binding:{browser.get('reason')}; bootstrap:{bootstrap.get('reason')}; html:{html.get('reason')}; api:{api.get('reason')}", "url": browser.get("url") or html.get("url"), "strategy": "service-binding+public-web-fallback", "bootstrap": bootstrap, "browser_fallback": browser}
    except Exception as exc:
        return {"listings": [], "next_page": None, "complete": True, "status": "degraded", "http_status": browser.get("http_status"), "reason": f"binding:{browser.get('reason')}; fallback:{type(exc).__name__}: {exc}", "url": browser.get("url"), "strategy": "service-binding+public-web-fallback"}


__all__ = ["search_vinted", "enrich_vinted_details", "DETAIL_BATCH_LIMIT", "VINTED_BASE", "VINTED_CATALOG_PAGE", "VINTED_CATALOG_API", "set_vinted_browser_binding", "reset_vinted_browser_binding", "_bootstrap_session", "_fetch_browser_worker"]
