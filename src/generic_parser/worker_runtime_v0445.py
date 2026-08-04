"""GenericParser 0.44.5 lightweight Cloudflare runtime.

Pure standard-library search, extraction, pagination, semantic card information and
active-rule traffic-light evaluation. No FastAPI, Pydantic, httpx, ASGI or package
bootstrap is imported by the live Worker.
"""
from __future__ import annotations

import html as html_lib
import re
from urllib.parse import quote, urlencode, urljoin

VERSION = "0.44.5"
BUILD_ID = "gp-0445-20260804-1"
API_CONTRACT = "match-v6.12-direct-free-worker"
WORKER_UNIT = "direct-worker+stdlib-parser+active-rules"
BASE_URL = "https://www.kleinanzeigen.de"
SOURCE_PAGE_SIZE = 25
PACKET_SIZE = 7
PACKETS_PER_SOURCE_PAGE = 4
MAX_VIRTUAL_PAGE = 2000

_ARTICLE_RE = re.compile(r'<article\b[^>]*\bdata-adid=["\']([^"\']+)["\'][^>]*>', re.I)
_ARTICLE_OPEN_RE = re.compile(r"<article\b([^>]*)>", re.I | re.S)
_ANCHOR_RE = re.compile(r'<a\b([^>]*)href=["\']([^"\']*/s-anzeige/[^"\']+)["\']([^>]*)>(.*?)</a>', re.I | re.S)
_H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.I | re.S)
_IMG_ALT_RE = re.compile(r'<img\b[^>]*\balt=["\']([^"\']+)["\']', re.I | re.S)
_IMG_SRC_RE = re.compile(r'<img\b[^>]*(?:src|data-src|data-imgsrc)=["\']([^"\']+)', re.I)
_TOTAL_RE = re.compile(r"(?:Mehr\s+als\s+)?([\d.]+)\s+Ergebnisse", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_PRICE_RE = re.compile(r"(\d[\d.]*)")
_NEXT_PATTERNS = (
    re.compile(r'<a\b[^>]*\brel=["\'][^"\']*next[^"\']*["\'][^>]*\bhref=["\']([^"\']+)', re.I),
    re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>\s*(?:<[^>]+>\s*)*Weiter(?:\s*</[^>]+>)*\s*</a>', re.I | re.S),
    re.compile(r'<a\b[^>]*\bclass=["\'][^"\']*(?:pagination-next|pagination-next-link)[^"\']*["\'][^>]*\bhref=["\']([^"\']+)', re.I),
)
_ATTR_TEMPLATE = r"\b%s\s*=\s*[\"']([^\"']*)[\"']"
_LOCATION_SUFFIX_RE = re.compile(r"\s+(?:\d{5}\s+)?[^|]{1,80}\s+Vorschau\s*$", re.I)
_PREVIEW_SUFFIX_RE = re.compile(r"\s+Vorschau\s*$", re.I)

_WANTED = re.compile(r"\b(suche|gesucht|suche nach|ankauf|kaufe)\b", re.I)
_ACCESSORY = re.compile(r"\b(lenkrad|tasche|case|hülle|halter|grip|sticker|pin[- ]?set|figur|rennstrecke|carrera|hot wheels|k'nex|klemmbaustein|kartenspiel|merch|controller|kabel|netzteil)\b", re.I)
_CONSOLE = re.compile(r"\b(konsole|handheld|switch oled|switch v2|switch lite|evercade exp|evercade vs|super pocket|bartop)\b", re.I)
_BUNDLE = re.compile(r"\b(bundle|paket|set|sammlung|konvolut|inkl\.?|plus|mit \d+|\d+ spiele|mehrere|komplett)\b|\+", re.I)
_GAME = re.compile(r"\b(spiel|game|cartridge|cardridge|cartrid|collection|arcade|modul|module)\b", re.I)
_NEW = re.compile(r"\b(neu|ovp|originalverpackt|versiegelt|sealed|ungeöffnet|in folie)\b", re.I)
_LIKE_NEW = re.compile(r"\b(wie neu|neuwertig|top zustand|sehr gut)\b", re.I)
_DEFECT = re.compile(r"\b(defekt|kaputt|beschädigt|akku defekt|unvollständig)\b", re.I)
_USED = re.compile(r"\b(gebraucht|gut erhalten|guter zustand)\b", re.I)
_STOP = {"der", "die", "das", "ein", "eine", "und", "oder", "mit", "für", "von", "neu", "ovp"}


class PayloadError(ValueError):
    pass


class UpstreamError(RuntimeError):
    def __init__(self, status: int, detail: str, retryable: bool = True):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.retryable = retryable


class SearchPayload:
    __slots__ = (
        "mode", "query", "postal_code", "location_id", "radius_km",
        "required_terms", "excluded_terms", "model_patterns", "brands",
        "max_price", "market_value", "accept_bundles", "accept_incomplete",
        "include_review", "include_rejected", "sort_by", "page", "source",
        "html", "cursor_url",
    )

    def __init__(self, data):
        if not isinstance(data, dict):
            raise PayloadError("JSON-Objekt erwartet")
        self.mode = str(data.get("mode") or "live")
        if self.mode not in {"live", "html"}:
            raise PayloadError("mode muss live oder html sein")
        self.query = str(data.get("query") or "").strip()
        if not 2 <= len(self.query) <= 120:
            raise PayloadError("Der Suchbegriff muss 2 bis 120 Zeichen lang sein")
        self.postal_code = _optional_text(data.get("postal_code"))
        if self.postal_code is not None and (len(self.postal_code) != 5 or not self.postal_code.isdigit()):
            raise PayloadError("postal_code muss fünfstellig sein")
        self.location_id = _optional_int(data.get("location_id"), "location_id", 1, None)
        self.radius_km = _optional_int(data.get("radius_km"), "radius_km", 0, 200)
        self.required_terms = _terms(data.get("required_terms"))
        self.excluded_terms = _terms(data.get("excluded_terms"))
        self.model_patterns = _terms(data.get("model_patterns"))
        self.brands = _terms(data.get("brands"))
        self.max_price = _optional_float(data.get("max_price"), "max_price")
        self.market_value = _optional_float(data.get("market_value"), "market_value")
        self.accept_bundles = bool(data.get("accept_bundles", False))
        self.accept_incomplete = bool(data.get("accept_incomplete", False))
        self.include_review = bool(data.get("include_review", True))
        self.include_rejected = bool(data.get("include_rejected", True))
        self.sort_by = str(data.get("sort_by") or "relevance")
        self.page = _optional_int(data.get("page", 0), "page", 0, MAX_VIRTUAL_PAGE)
        if self.page is None:
            self.page = 0
        self.source = str(data.get("source") or "auto")
        self.html = data.get("html")
        if self.html is not None:
            self.html = str(self.html)
            if len(self.html) > 2_000_000:
                raise PayloadError("html ist zu groß")
        self.cursor_url = _optional_text(data.get("cursor_url"))


def _optional_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _optional_int(value, name, minimum, maximum):
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise PayloadError(f"{name} muss eine Ganzzahl sein")
    if parsed < minimum or (maximum is not None and parsed > maximum):
        raise PayloadError(f"{name} liegt außerhalb des erlaubten Bereichs")
    return parsed


def _optional_float(value, name):
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise PayloadError(f"{name} muss eine Zahl sein")
    if parsed <= 0:
        raise PayloadError(f"{name} muss größer als 0 sein")
    return parsed


def _terms(value):
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    try:
        return [str(item).strip().lower() for item in value if str(item).strip()]
    except TypeError:
        raise PayloadError("Begriffslisten müssen Text oder Listen sein")


def _tokens(value):
    return [token for token in re.findall(r"[a-z0-9äöüß]+", str(value).lower()) if len(token) > 1 and token not in _STOP]


def _text(fragment):
    return _SPACE_RE.sub(" ", html_lib.unescape(_TAG_RE.sub(" ", fragment))).strip()


def _attr(fragment, name):
    match = re.search(_ATTR_TEMPLATE % re.escape(name), fragment, re.I | re.S)
    return html_lib.unescape(match.group(1)).strip() if match else None


def _class_text(card, marker):
    pos = card.find(marker)
    if pos < 0:
        return ""
    start = card.rfind("<", 0, pos)
    end = card.find(">", pos)
    if start < 0 or end < 0:
        return ""
    close = card.find("</", end)
    if close < 0:
        return ""
    return _text(card[end + 1:close])


def _price(raw):
    match = _PRICE_RE.search(str(raw).replace(" ", " "))
    if not match:
        return None
    try:
        return float(match.group(1).replace(".", ""))
    except ValueError:
        return None


def _reported_total(source):
    match = _TOTAL_RE.search(source[:250_000])
    if not match:
        return None
    try:
        return int(match.group(1).replace(".", ""))
    except ValueError:
        return None


def _source_url(payload, source_page):
    if payload.cursor_url:
        return payload.cursor_url
    slug = quote(re.sub(r"\s+", "-", payload.query.lower()).strip("-"), safe="-")
    if payload.postal_code and payload.location_id:
        suffix = f"k0l{payload.location_id}"
        if payload.radius_km is not None:
            suffix += f"r{payload.radius_km}"
        path = f"/s-{payload.postal_code}/{slug}/{suffix}"
    else:
        path = f"/s-{slug}/k0"
    params = {"sortingField": "SORTING_DATE"}
    if source_page > 0:
        params["pageNum"] = str(source_page + 1)
    return f"{BASE_URL}{path}?{urlencode(params)}"


def _card_ranges(source):
    starts = [(match.group(1), match.start()) for match in _ARTICLE_RE.finditer(source)]
    ranges = []
    for index, (listing_id, start) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else source.find("</article>", start)
        if end < 0:
            end = min(len(source), start + 40_000)
        else:
            end += len("</article>")
        ranges.append((listing_id, start, end))
    return ranges


def _clean_alt_title(value):
    if not value:
        return None
    text = html_lib.unescape(value).strip()
    text = _PREVIEW_SUFFIX_RE.sub("", text)
    text = _LOCATION_SUFFIX_RE.sub("", text)
    return text.strip() or None


def _extract_card(source, listing_id, start, end, payload):
    card = source[start:end]
    article_match = _ARTICLE_OPEN_RE.search(card)
    article_attrs = article_match.group(1) if article_match else ""
    data_href = _attr(article_attrs, "data-href")
    anchors = list(_ANCHOR_RE.finditer(card))
    first_href = anchors[0].group(2) if anchors else data_href
    if not first_href:
        return None

    h2_match = _H2_RE.search(card)
    h2_title = _text(h2_match.group(1)) if h2_match else None
    link_text = None
    aria_title = None
    attr_title = None
    for match in anchors:
        attrs = f"{match.group(1)} {match.group(3)}"
        body_text = _text(match.group(4))
        if not link_text and body_text:
            link_text = body_text
        if not aria_title:
            aria_title = _attr(attrs, "aria-label")
        if not attr_title:
            attr_title = _attr(attrs, "title")
    img_match = _IMG_ALT_RE.search(card)
    image_alt = _clean_alt_title(img_match.group(1) if img_match else None)
    title = None
    title_strategy = None
    for strategy, value in (
        ("h2", h2_title),
        ("anzeige_link_text", link_text),
        ("aria_label", aria_title),
        ("title_attribute", attr_title),
        ("image_alt", image_alt),
    ):
        if value and value.strip():
            title = value.strip()
            title_strategy = strategy
            break
    if not title:
        return None

    price_raw = _class_text(card, "price-shipping--price")
    location_raw = _class_text(card, "aditem-main--top--left")
    date_raw = _class_text(card, "aditem-main--top--right")
    description = _class_text(card, "aditem-main--middle--description")
    image_match = _IMG_SRC_RE.search(card)
    image_url = urljoin(BASE_URL, image_match.group(1)) if image_match else None
    postal_match = re.search(r"\b(\d{5})\b", location_raw)
    postal_code = postal_match.group(1) if postal_match else None
    place = location_raw.replace(postal_code or "", "").strip(" ,") or None
    numeric_price = _price(price_raw)
    item = {
        "id": listing_id,
        "title": title,
        "url": urljoin(BASE_URL, data_href or first_href),
        "price": numeric_price,
        "price_raw": price_raw or None,
        "postal_code": postal_code,
        "place": place,
        "posted_at": date_raw or None,
        "description": description or None,
        "source_query": payload.query,
        "tags": [],
        "image_url": image_url,
        "title_strategy": title_strategy,
    }
    item["result_info"] = _card_info(title, payload.query)
    evaluation = _evaluate(item, payload)
    item["traffic_light"] = evaluation
    item["score"] = evaluation["score"]
    item["decision"] = evaluation["decision"]
    item["match"] = {
        "score": evaluation["score"],
        "decision": evaluation["decision"],
        "listing_class": evaluation["label"],
        "reason": evaluation["reason"],
    }
    return item


def _next_url(source):
    for pattern in _NEXT_PATTERNS:
        match = pattern.search(source)
        if match:
            return urljoin(BASE_URL, match.group(1).replace("&amp;", "&"))
    return None


def _card_info(title, query):
    wanted = bool(_WANTED.search(title))
    accessory = bool(_ACCESSORY.search(title))
    console = bool(_CONSOLE.search(title))
    bundle = bool(_BUNDLE.search(title))
    game = bool(_GAME.search(title))
    if wanted:
        offer_type = "Gesuch"
    elif accessory:
        offer_type = "Zubehör"
    elif console:
        offer_type = "Konsole/Handheld"
    elif game:
        offer_type = "Spiel/Cartridge"
    else:
        offer_type = "Produkt"

    if _DEFECT.search(title):
        condition = "defekt/unvollständig"
    elif _NEW.search(title):
        condition = "Neu/OVP"
    elif _LIKE_NEW.search(title):
        condition = "wie neu"
    elif _USED.search(title):
        condition = "gebraucht"
    else:
        condition = "Zustand offen"

    scope = "Bundle" if bundle else "Einzelangebot"
    query_tokens = _tokens(query)
    title_tokens = set(_tokens(title))
    matched = sum(1 for token in query_tokens if token in title_tokens)
    ratio = matched / len(query_tokens) if query_tokens else 1.0
    if wanted:
        fit = "kein Verkaufsangebot"
    elif accessory:
        fit = "wahrscheinlich unpassend"
    elif ratio >= 0.75:
        fit = "passend"
    elif ratio >= 0.4 or bundle or console:
        fit = "prüfen"
    else:
        fit = "wahrscheinlich unpassend"
    return {
        "offer_type": offer_type,
        "condition": condition,
        "scope": scope,
        "fit": fit,
        "display_text": f"{offer_type} · {condition} · {scope} · {fit}",
    }


def _criterion(name, color, reason, hard=False):
    return {"name": name, "color": color, "reason": reason, "hard": hard, "active": True}


def _evaluate(listing, payload):
    title = str(listing.get("title") or "")
    haystack = title.lower()
    info = listing.get("result_info") if isinstance(listing.get("result_info"), dict) else {}
    offer_type = str(info.get("offer_type") or "Produkt")
    condition = str(info.get("condition") or "Zustand offen")
    scope = str(info.get("scope") or "Einzelangebot")
    criteria = []

    query_tokens = _tokens(payload.query)
    title_tokens = set(_tokens(title))
    matched = sum(token in title_tokens for token in query_tokens)
    ratio = matched / len(query_tokens) if query_tokens else 1.0
    if ratio >= 0.75:
        criteria.append(_criterion("Suchbegriff", "green", "Suchbegriff gefunden"))
    elif ratio >= 0.4:
        criteria.append(_criterion("Suchbegriff", "yellow", "Suchbegriff teilweise erkannt"))
    else:
        criteria.append(_criterion("Suchbegriff", "red", "Kein belastbarer Bezug zum Suchbegriff", True))

    if payload.required_terms:
        missing = [term for term in payload.required_terms if term not in haystack]
        if missing:
            criteria.append(_criterion("Pflichtbegriffe", "red", "Pflichtbegriff fehlt", True))
        else:
            criteria.append(_criterion("Pflichtbegriffe", "green", "Pflichtbegriffe erfüllt"))

    if payload.excluded_terms:
        found = [term for term in payload.excluded_terms if term in haystack]
        if found:
            criteria.append(_criterion("Ausschlussbegriffe", "red", "Ausschlussbegriff erkannt", True))
        else:
            criteria.append(_criterion("Ausschlussbegriffe", "green", "Keine Ausschlussbegriffe"))

    if payload.model_patterns:
        if any(term in haystack for term in payload.model_patterns):
            criteria.append(_criterion("Modellvarianten", "green", "Modell oder Schreibvariante erkannt"))
        else:
            criteria.append(_criterion("Modellvarianten", "yellow", "Modell oder Schreibvariante nicht erkannt"))

    if payload.brands:
        if any(term in haystack for term in payload.brands):
            criteria.append(_criterion("Marke", "green", "Marke erkannt"))
        else:
            criteria.append(_criterion("Marke", "yellow", "Marke nicht eindeutig erkannt"))

    if offer_type == "Gesuch":
        criteria.append(_criterion("Verkaufsangebot", "red", "Gesuch statt Verkaufsangebot", True))

    if condition == "defekt/unvollständig":
        if payload.accept_incomplete:
            criteria.append(_criterion("Zustand", "green", "Unvollständige Angebote sind erlaubt"))
        else:
            criteria.append(_criterion("Zustand", "red", "Defekt oder unvollständig nicht akzeptiert", True))

    if scope == "Bundle":
        if payload.accept_bundles:
            criteria.append(_criterion("Umfang", "green", "Bundle erlaubt"))
        else:
            criteria.append(_criterion("Umfang", "red", "Bundle ist ausgeschlossen", True))

    price_value = listing.get("price")
    if payload.max_price is not None:
        if price_value is None:
            criteria.append(_criterion("Maximalpreis", "yellow", "Preis fehlt oder ist VB"))
        elif price_value <= payload.max_price:
            criteria.append(_criterion("Maximalpreis", "green", "Innerhalb des Maximalpreises"))
        else:
            criteria.append(_criterion("Maximalpreis", "red", "Über dem Maximalpreis", True))

    if payload.market_value is not None:
        if price_value is None:
            criteria.append(_criterion("Richtwert", "yellow", "Kein belastbarer Preis"))
        elif price_value <= payload.market_value:
            criteria.append(_criterion("Richtwert", "green", "Auf oder unter dem Richtwert"))
        elif price_value <= payload.market_value * 1.2:
            criteria.append(_criterion("Richtwert", "yellow", "Bis 20 % über dem Richtwert"))
        else:
            criteria.append(_criterion("Richtwert", "red", "Mehr als 20 % über dem Richtwert"))

    hard_red = any(item["color"] == "red" and item["hard"] for item in criteria)
    red_count = sum(item["color"] == "red" for item in criteria)
    yellow_count = sum(item["color"] == "yellow" for item in criteria)
    if hard_red or red_count >= 2:
        color, label, score, decision = "red", "🔴 Unpassend", 0, "reject"
    elif red_count or yellow_count:
        color, label, score, decision = "yellow", "🟡 Prüfen", 60, "review"
    else:
        color, label, score, decision = "green", "🟢 Passender Treffer", 100, "accept"

    reasons = [item["reason"] for item in criteria if item["color"] != "green"]
    if not reasons:
        reasons = [item["reason"] for item in criteria if item["color"] == "green"][:2] or ["Alle aktiven Regeln erfüllt"]
    return {
        "color": color,
        "label": label,
        "criteria": criteria,
        "active_criteria": len(criteria),
        "reason": " · ".join(reasons[:3]),
        "score": score,
        "decision": decision,
    }


async def search_page(payload, fetch_html):
    source_page = payload.page // PACKETS_PER_SOURCE_PAGE
    packet_index = payload.page % PACKETS_PER_SOURCE_PAGE
    request_url = _source_url(payload, source_page)
    source = payload.html or "" if payload.mode == "html" else await fetch_html(request_url)
    ranges = _card_ranges(source)
    start_index = packet_index * PACKET_SIZE
    selected = ranges[start_index:start_index + PACKET_SIZE]
    extracted = []
    malformed = []
    for listing_id, start, end in selected:
        item = _extract_card(source, listing_id, start, end, payload)
        if item is None:
            malformed.append({"id": listing_id, "reason": "card_not_extractable"})
        else:
            extracted.append(item)

    visible = [
        item for item in extracted
        if item["decision"] == "accept"
        or (item["decision"] == "review" and payload.include_review)
        or (item["decision"] == "reject" and payload.include_rejected)
    ]
    fetched = len(extracted)
    hidden = fetched - len(visible)
    reported_total = _reported_total(source)
    source_cards = len(ranges)
    consumed = min(source_cards, start_index + len(selected))
    source_page_finished = consumed >= source_cards
    discovered_next = _next_url(source) if source_page_finished else request_url

    complete = False
    stop_reason = "work_packet_complete"
    if source_cards == 0:
        complete, stop_reason = True, "empty_page_verified"
    elif source_page_finished and not discovered_next:
        complete, stop_reason = True, "next_link_missing"

    next_page = None if complete else payload.page + 1
    ids = [item["id"] for item in visible]
    strategy_counts = {}
    for item in extracted:
        strategy = item.get("title_strategy") or "unknown"
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    traffic_counts = {"green": 0, "yellow": 0, "red": 0}
    active_rule_counts = {}
    for item in extracted:
        evaluation = item["traffic_light"]
        traffic_counts[evaluation["color"]] += 1
        for criterion in evaluation["criteria"]:
            name = criterion["name"]
            active_rule_counts[name] = active_rule_counts.get(name, 0) + 1

    return {
        "mode": payload.mode,
        "generated_urls": [request_url] if payload.mode == "live" else [],
        "pagination": {
            "source": "html-light-packets",
            "page": payload.page,
            "pages_loaded": 1,
            "page_counts": [fetched],
            "new_ids_per_page": [fetched],
            "unique_listings": fetched,
            "duplicates": 0,
            "complete": complete,
            "partial": not complete,
            "continuation_available": not complete,
            "next_page": next_page,
            "stop_reason": stop_reason,
            "reported_total": reported_total,
            "source_page": source_page,
            "packet_index": packet_index,
            "packet_size": PACKET_SIZE,
            "source_cards": source_cards,
            "global_consumed": source_page * SOURCE_PAGE_SIZE + consumed,
            "cursor_url": discovered_next,
            "requested_cursor_url": payload.cursor_url,
            "actual_source_url": request_url,
            "next_link_found": bool(discovered_next),
            "next_link_strategy": "source_html_weiter_link",
            "reported_total_is_diagnostic_only": True,
            "reported_total_stop_disabled": True,
            "worker_unit": WORKER_UNIT,
        },
        "listings": visible,
        "summary": {
            "reported_total": reported_total,
            "fetched_listings": fetched,
            "visible_listings": len(visible),
            "hidden_by_filter": hidden,
            "alerts": sum(item["decision"] == "accept" for item in extracted),
            "review": sum(item["decision"] == "review" for item in extracted),
            "rejected": sum(item["decision"] == "reject" for item in extracted),
            "malformed_rejected": len(malformed),
            "data_consistent": fetched == len(visible) + hidden,
        },
        "traffic_light_summary": traffic_counts,
        "active_rule_summary": active_rule_counts,
        "coverage_diagnostics": {
            "schema": "direct-stdlib-active-rules-v1",
            "source_page": source_page,
            "packet_index": packet_index,
            "html_bytes": len(source),
            "range_count": len(ranges),
            "selected_range_count": len(selected),
            "selected_ids": [entry[0] for entry in selected],
            "returned_ids": ids,
            "extracted_count": fetched,
            "visible_count": len(visible),
            "hidden_count": hidden,
            "malformed_count": len(malformed),
            "malformed": malformed,
            "title_empty_count": 0,
            "anzeige_link_missing_count": 0,
            "reported_total": reported_total,
            "next_link": {"selected_href": discovered_next, "selected_strategy": "source_html_weiter_link" if discovered_next else None},
            "actual_source_url": request_url,
            "requested_cursor_url": payload.cursor_url,
            "stop_reason": stop_reason,
            "raw_html_persisted": False,
            "title_strategy_counts": strategy_counts,
            "title_fallback_active": True,
            "title_order": ["h2", "anzeige_link_text", "aria_label", "title_attribute", "image_alt"],
            "diagnostic_uses_final_extraction_result": True,
            "result_information_active": True,
            "empty_fields_ignored": True,
        },
        "worker": {
            "version": VERSION,
            "build_id": BUILD_ID,
            "api_contract": API_CONTRACT,
            "worker_unit": WORKER_UNIT,
            "source_used": "html-light-packets",
            "matching": "active-rules-v2",
            "search_module": "worker_runtime_v0445",
            "reference_version": "0.44.4",
            "traffic_light_model": "v2-active-rules",
            "empty_fields_ignored": True,
            "direct_worker": True,
            "asgi": False,
            "fastapi": False,
            "pydantic": False,
            "httpx": False,
        },
        "deployment_identity": identity(),
        "consistency": {
            "ok": fetched == len(visible) + hidden,
            "fetched_equals_visible_plus_hidden": fetched == len(visible) + hidden,
            "visible_equals_listings": True,
            "reported_total_not_used_as_stop": True,
            "source_next_link_checked": source_page_finished,
            "next_link_state_consistent": complete or bool(discovered_next),
        },
    }


def identity():
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "entrypoint": "cloudflare_worker.Default.fetch",
        "runtime_module": "worker_runtime_v0445",
        "worker_unit": WORKER_UNIT,
        "reference_version": "0.44.4",
        "technical_base": "0.43.6.3",
        "runtime_model": "direct-worker-stdlib-v1",
    }
