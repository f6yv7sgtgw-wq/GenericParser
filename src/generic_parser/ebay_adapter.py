"""Official eBay Browse API adapter for GenericParser.

The adapter uses an Application access token minted with the client-credentials
grant and searches the German marketplace. Credentials and tokens are kept only
in request/isolate memory. Listing responses are normalized and returned to the
caller without server-side persistence.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from contextvars import ContextVar
from typing import Any
from urllib.parse import urlencode

import httpx

EBAY_MARKETPLACE = "EBAY_DE"
EBAY_COUNTRY = "DE"
EBAY_CURRENCY = "EUR"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_PUBLIC_SEARCH_URL = "https://www.ebay.de/sch/i.html"
EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope"
PAGE_SIZE = 25
MAX_OFFSET = 9_999
TOKEN_EXPIRY_SAFETY_SECONDS = 60

_EBAY_CREDENTIALS: ContextVar[tuple[str, str] | None] = ContextVar(
    "ebay_credentials", default=None
)
_TOKEN_CACHE: dict[str, Any] = {}
_TOKEN_LOCK = asyncio.Lock()


class EbayAdapterError(RuntimeError):
    """Sanitized eBay transport error safe for source diagnostics."""

    def __init__(self, reason: str, *, http_status: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.http_status = http_status


def set_ebay_credentials(client_id: Any, client_secret: Any):
    client_id_text = str(client_id or "").strip()
    client_secret_text = str(client_secret or "").strip()
    credentials = (
        (client_id_text, client_secret_text)
        if client_id_text and client_secret_text
        else None
    )
    return _EBAY_CREDENTIALS.set(credentials)


def reset_ebay_credentials(token) -> None:
    _EBAY_CREDENTIALS.reset(token)


def ebay_credentials_configured() -> bool:
    return _EBAY_CREDENTIALS.get() is not None


def _reset_token_cache_for_tests() -> None:
    _TOKEN_CACHE.clear()


def _credential_fingerprint(credentials: tuple[str, str]) -> str:
    client_id, client_secret = credentials
    return hashlib.sha256(
        f"{client_id}\0{client_secret}".encode("utf-8")
    ).hexdigest()


def _money(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("value") or value.get("amount") or value.get("price")
    try:
        return round(float(str(value).replace("€", "").replace(" ", "").replace(",", ".")), 2)
    except (TypeError, ValueError):
        return None


def _currency(value: Any) -> str:
    if isinstance(value, dict):
        currency = str(value.get("currency") or "").upper()
        if currency:
            return currency
    return EBAY_CURRENCY


def _condition_text(value: Any) -> str:
    status = str(value or "").casefold()
    if any(term in status for term in ("neu", "new", "unbenutzt", "new other")):
        return "Neu/OVP"
    if any(term in status for term in ("sehr gut", "very good", "wie neu", "like new")):
        return "wie neu"
    if any(term in status for term in ("defekt", "ersatzteil", "parts", "not working")):
        return "defekt/unvollständig"
    if any(term in status for term in ("gut", "good", "gebraucht", "used", "acceptable")):
        return "gebraucht"
    return "Zustand offen"


def _shipping(item: dict[str, Any]) -> tuple[float | None, bool | None, bool]:
    """Return cost, availability and whether the total is trustworthy."""

    options = item.get("shippingOptions")
    options = options if isinstance(options, list) else []
    costs = [
        cost
        for option in options
        if isinstance(option, dict)
        and (cost := _money(option.get("shippingCost"))) is not None
    ]
    if costs:
        return min(costs), True, True
    if options:
        return None, True, False
    pickups = item.get("pickupOptions")
    if isinstance(pickups, list) and pickups:
        return 0.0, False, True
    return None, None, False


def _price_text(
    item_price: float | None,
    shipping_cost: float | None,
    total_price: float | None,
    *,
    shipping_available: bool | None,
) -> str | None:
    if item_price is None:
        return None
    if total_price is None:
        return f"{item_price:g} € + Versand offen"
    if shipping_available is False:
        return f"{total_price:g} € · Abholung"
    if shipping_cost == 0:
        return f"{total_price:g} € inkl. Versand"
    return f"{item_price:g} € + {shipping_cost:g} € Versand = {total_price:g} €"


def _normalize_item(
    item: dict[str, Any],
    query: str,
    *,
    include_auctions: bool,
) -> dict[str, Any] | None:
    item_id = str(item.get("itemId") or item.get("legacyItemId") or "").strip()
    title = str(item.get("title") or "").strip()
    url = str(item.get("itemWebUrl") or "").strip()
    if not item_id or not title or not url.startswith("https://"):
        return None

    buying_options = [
        str(option).upper()
        for option in (item.get("buyingOptions") or [])
        if str(option).strip()
    ]
    fixed_price = "FIXED_PRICE" in buying_options
    auction_only = "AUCTION" in buying_options and not fixed_price
    if auction_only and not include_auctions:
        return None

    raw_price = item.get("currentBidPrice") if auction_only else item.get("price")
    item_price = _money(raw_price)
    currency = _currency(raw_price or item.get("price"))
    shipping_cost, shipping_available, total_known = _shipping(item)
    total_price = (
        round(item_price + (shipping_cost or 0.0), 2)
        if item_price is not None and total_known
        else None
    )

    location = item.get("itemLocation")
    location = location if isinstance(location, dict) else {}
    image = item.get("image")
    image = image if isinstance(image, dict) else {}
    seller = item.get("seller")
    seller = seller if isinstance(seller, dict) else {}
    condition = _condition_text(item.get("condition"))
    listing_format = "Auktion" if auction_only else "Sofort-Kaufen"
    if "BEST_OFFER" in buying_options and not auction_only:
        listing_format += " + Preisvorschlag"
    lot_size = item.get("lotSize")
    scope = "Bundle" if isinstance(lot_size, int) and lot_size > 1 else "Einzelangebot"

    return {
        "id": f"ebay:{item_id}",
        "title": title,
        "url": url,
        # The established scoring field is a total only when shipping is known.
        "price": total_price,
        "price_raw": _price_text(
            item_price,
            shipping_cost,
            total_price,
            shipping_available=shipping_available,
        ),
        "item_price": item_price,
        "shipping_cost": shipping_cost,
        "total_price": total_price,
        "currency": currency,
        "shipping_available": shipping_available,
        "postal_code": location.get("postalCode"),
        "place": location.get("city") or location.get("stateOrProvince"),
        "posted_at": item.get("itemOriginDate") or item.get("itemCreationDate"),
        "item_end_date": item.get("itemEndDate"),
        "description": str(item.get("shortDescription") or "").strip() or None,
        "source_query": query,
        "source": "ebay",
        "source_label": "eBay",
        "tags": [],
        "image_url": image.get("imageUrl"),
        "buying_options": buying_options,
        "listing_format": listing_format,
        "auction": auction_only,
        "bid_count": item.get("bidCount"),
        "seller": {
            "username": seller.get("username"),
            "feedback_percentage": seller.get("feedbackPercentage"),
            "feedback_score": seller.get("feedbackScore"),
        },
        "transient": True,
        "result_info": {
            "offer_type": "Produkt",
            "condition": condition,
            "scope": scope,
            "fit": "prüfen",
            "listing_format": listing_format,
            "display_text": f"eBay · {condition} · {listing_format}",
        },
    }


def _safe_error_reason(response: httpx.Response, prefix: str) -> str:
    try:
        body = response.json()
    except Exception:
        body = {}
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            error_id = str(errors[0].get("errorId") or "unknown")
            domain = str(errors[0].get("domain") or "unknown")
            return f"{prefix}:{domain}/{error_id}"
        oauth_error = str(body.get("error") or "").strip()
        if oauth_error:
            return f"{prefix}:{oauth_error}"
    return f"{prefix}:http_{response.status_code}"


async def _application_token(client: httpx.AsyncClient) -> str:
    credentials = _EBAY_CREDENTIALS.get()
    if credentials is None:
        raise EbayAdapterError("ebay_credentials_unavailable")

    fingerprint = _credential_fingerprint(credentials)
    now = time.monotonic()
    if (
        _TOKEN_CACHE.get("fingerprint") == fingerprint
        and _TOKEN_CACHE.get("token")
        and float(_TOKEN_CACHE.get("expires_at") or 0) > now
    ):
        return str(_TOKEN_CACHE["token"])

    async with _TOKEN_LOCK:
        now = time.monotonic()
        if (
            _TOKEN_CACHE.get("fingerprint") == fingerprint
            and _TOKEN_CACHE.get("token")
            and float(_TOKEN_CACHE.get("expires_at") or 0) > now
        ):
            return str(_TOKEN_CACHE["token"])

        client_id, client_secret = credentials
        try:
            response = await client.post(
                EBAY_TOKEN_URL,
                auth=httpx.BasicAuth(client_id, client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials", "scope": EBAY_SCOPE},
            )
        except Exception as exc:
            raise EbayAdapterError(
                f"ebay_oauth_transport:{type(exc).__name__}"
            ) from exc
        if response.status_code != 200:
            raise EbayAdapterError(
                _safe_error_reason(response, "ebay_oauth"),
                http_status=response.status_code,
            )
        try:
            payload = response.json()
        except Exception as exc:
            raise EbayAdapterError(
                "ebay_oauth_non_json", http_status=response.status_code
            ) from exc
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise EbayAdapterError(
                "ebay_oauth_token_missing", http_status=response.status_code
            )
        try:
            expires_in = max(120, int(payload.get("expires_in") or 7200))
        except (TypeError, ValueError):
            expires_in = 7200
        _TOKEN_CACHE.update(
            {
                "fingerprint": fingerprint,
                "token": token,
                "expires_at": time.monotonic()
                + max(1, expires_in - TOKEN_EXPIRY_SAFETY_SECONDS),
            }
        )
        return token


def _public_search_url(query: str, page: int) -> str:
    params = {"_nkw": query}
    if page > 0:
        params["_pgn"] = str(page + 1)
    return f"{EBAY_PUBLIC_SEARCH_URL}?{urlencode(params)}"


async def search_ebay(
    query: str,
    *,
    page: int = 0,
    include_auctions: bool = False,
    sort_by: str = "relevance",
    postal_code: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    page = max(0, int(page))
    offset = page * PAGE_SIZE
    public_url = _public_search_url(query, page)
    if offset > MAX_OFFSET:
        return {
            "listings": [],
            "status": "ok",
            "http_status": None,
            "reason": "ebay_offset_limit_reached",
            "strategy": "official-browse-api",
            "url": public_url,
            "complete": True,
            "next_page": None,
            "reported_total": None,
            "transient": True,
        }

    if not ebay_credentials_configured():
        return {
            "listings": [],
            "status": "degraded",
            "http_status": None,
            "reason": "ebay_credentials_unavailable",
            "strategy": "official-browse-api",
            "marketplace": EBAY_MARKETPLACE,
            "url": public_url,
            "complete": True,
            "next_page": None,
            "reported_total": None,
            "include_auctions": include_auctions,
            "transient": True,
        }

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
            trust_env=False,
        )
    try:
        token = await _application_token(client)
        # Browse keyword search already returns FIXED_PRICE offers by default.
        # The buyingOptions filter is therefore needed only to opt into
        # auction-only listings; normalization applies the default-off rule
        # defensively as well.
        filters = ["deliveryCountry:DE"]
        if include_auctions:
            filters.append("buyingOptions:{FIXED_PRICE|AUCTION}")
        if postal_code:
            filters.insert(0, f"deliveryPostalCode:{postal_code}")
        params: dict[str, str] = {
            "q": query,
            "limit": str(PAGE_SIZE),
            "offset": str(offset),
            "filter": ",".join(filters),
            "fieldgroups": "EXTENDED",
        }
        sort = {
            "date": "newlyListed",
            "price_asc": "price",
            "price_desc": "-price",
        }.get(str(sort_by or "relevance"))
        if sort:
            params["sort"] = sort
        context = "contextualLocation=country=DE"
        if postal_code:
            context += f",zip={postal_code}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": EBAY_MARKETPLACE,
            "X-EBAY-C-ENDUSERCTX": context,
            "Accept-Language": "de-DE",
            "Accept": "application/json",
        }
        try:
            response = await client.get(EBAY_SEARCH_URL, params=params, headers=headers)
        except Exception as exc:
            raise EbayAdapterError(
                f"ebay_browse_transport:{type(exc).__name__}"
            ) from exc
        if response.status_code != 200:
            raise EbayAdapterError(
                _safe_error_reason(response, "ebay_browse"),
                http_status=response.status_code,
            )
        try:
            body = response.json()
        except Exception as exc:
            raise EbayAdapterError(
                "ebay_browse_non_json", http_status=response.status_code
            ) from exc
        raw_items = body.get("itemSummaries")
        raw_items = raw_items if isinstance(raw_items, list) else []
        listings = [
            listing
            for raw in raw_items
            if isinstance(raw, dict)
            and (
                listing := _normalize_item(
                    raw, query, include_auctions=include_auctions
                )
            )
            is not None
        ]
        next_page = (
            page + 1
            if body.get("next") and offset + PAGE_SIZE <= MAX_OFFSET
            else None
        )
        try:
            total = int(body.get("total")) if body.get("total") is not None else None
        except (TypeError, ValueError):
            total = None
        return {
            "listings": listings,
            "status": "ok",
            "http_status": response.status_code,
            "reason": None,
            "strategy": "official-browse-api",
            "marketplace": EBAY_MARKETPLACE,
            "url": public_url,
            "complete": next_page is None,
            "next_page": next_page,
            "reported_total": total,
            "raw_count": len(raw_items),
            "auction_only_filtered": len(raw_items) - len(listings),
            "include_auctions": include_auctions,
            "page_size": PAGE_SIZE,
            "transient": True,
        }
    except EbayAdapterError as exc:
        return {
            "listings": [],
            "status": "degraded",
            "http_status": exc.http_status,
            "reason": exc.reason,
            "strategy": "official-browse-api",
            "marketplace": EBAY_MARKETPLACE,
            "url": public_url,
            "complete": True,
            "next_page": None,
            "reported_total": None,
            "include_auctions": include_auctions,
            "transient": True,
        }
    finally:
        if owns_client:
            await client.aclose()


__all__ = [
    "search_ebay",
    "set_ebay_credentials",
    "reset_ebay_credentials",
    "ebay_credentials_configured",
    "EBAY_MARKETPLACE",
    "PAGE_SIZE",
]
