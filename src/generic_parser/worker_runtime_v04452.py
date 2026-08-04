"""GenericParser 0.44.5.2 pagination, price and diagnostics hotfix.

Keeps the direct standard-library Worker from 0.44.5.1. Result-card windows are
bounded by the complete Kleinanzeigen list item where possible, navigation-only
link candidates are removed, explicit Euro prices are recovered, and a finished
source page advances to the next four-packet boundary for cursor navigation.
"""
from __future__ import annotations

import html as html_lib
import re

import worker_runtime_v04451 as previous

VERSION = "0.44.5.2"
BUILD_ID = "gp-04452-20260804-1"
API_CONTRACT = "match-v6.12.2-cursor-price-diagnostics"
WORKER_UNIT = "direct-worker+cursor-pagination+price-fallback+diagnostics"
BASE_URL = previous.BASE_URL
SOURCE_PAGE_SIZE = previous.SOURCE_PAGE_SIZE
PACKET_SIZE = previous.PACKET_SIZE
PACKETS_PER_SOURCE_PAGE = previous.PACKETS_PER_SOURCE_PAGE
MAX_VIRTUAL_PAGE = previous.MAX_VIRTUAL_PAGE

PayloadError = previous.PayloadError
UpstreamError = previous.UpstreamError
ParserLayoutError = previous.ParserLayoutError
SearchPayload = previous.SearchPayload

_NAVIGATION_TITLES = {
    "navigation", "zurück", "weiter", "vorheriges bild", "nächstes bild",
    "anzeige merken", "bildergalerie",
}
_PRICE_CLASS_RE = re.compile(
    r'<(?:div|span|p)\b[^>]*class=["\'][^"\']*(?:price|preis)[^"\']*["\'][^>]*>(.*?)</(?:div|span|p)>',
    re.I | re.S,
)
_EXPLICIT_EURO_RE = re.compile(
    r'(?<!\d)(\d{1,3}(?:\.\d{3})*|\d{1,6})(?:[,.](\d{2}))?\s*(?:€|EUR)(?![A-Za-z])',
    re.I,
)
_DATA_PRICE_RE = re.compile(
    r'(?:data-price|data-adprice|"price")\s*(?:=|:)\s*["\']?\s*(\d{1,7}(?:[,.]\d{1,2})?)',
    re.I,
)
_ANCHOR_BODY_RE = re.compile(
    r'<a\b[^>]*\bhref=["\'][^"\']*/s-anzeige/[^"\']+["\'][^>]*>(.*?)</a>',
    re.I | re.S,
)


def _title_hint(card):
    h2 = previous.base._H2_RE.search(card)
    if h2:
        text = previous.base._text(h2.group(1)).strip()
        if text:
            return text
    anchor = _ANCHOR_BODY_RE.search(card)
    if anchor:
        text = previous.base._text(anchor.group(1)).strip()
        if text:
            return text
    aria = re.search(r'\baria-label=["\']([^"\']+)["\']', card, re.I)
    return html_lib.unescape(aria.group(1)).strip() if aria else ""


def _is_navigation_candidate(card):
    title = _title_hint(card).casefold().strip(" .:-")
    return title in _NAVIGATION_TITLES or title.startswith("navigation ")


def _preferred_start(source, lower, anchor):
    # The complete list item is preferable to an inner aditem div; the latter
    # caused all prices to fall outside the extraction window in 0.44.5.1.
    for markers in (
        ('<li class="ad-listitem', "<li class='ad-listitem"),
        ("<article",),
        ('<div class="ad-listitem', "<div class='ad-listitem"),
        ('<div class="aditem', "<div class='aditem"),
    ):
        positions = [source.rfind(marker, lower, anchor + 1) for marker in markers]
        positions = [position for position in positions if position >= 0]
        if positions:
            return max(positions)
    return lower


def _wide_container_end(source, start, anchor_end, upper):
    prefix = source[start:start + 64].lower()
    if prefix.startswith("<li"):
        closing = "</li>"
    elif prefix.startswith("<article"):
        closing = "</article>"
    else:
        # A nested div cannot be closed safely with the first </div>. The next
        # unique listing link is the safer bounded end and contains price/meta.
        return upper
    position = source.find(closing, anchor_end, min(len(source), upper + 40_000))
    return position + len(closing) if position >= 0 else upper


def _wide_link_ranges(source):
    groups, raw_count = previous._link_groups(source)
    ranges = []
    removed_navigation = []
    for index, group in enumerate(groups):
        previous_last = groups[index - 1]["last"] if index else 0
        next_first = groups[index + 1]["first"] if index + 1 < len(groups) else len(source)
        lower = max(previous_last, group["first"] - 25_000, 0)
        upper = min(next_first, group["last"] + 45_000, len(source))
        start = _preferred_start(source, lower, group["first"])
        end = _wide_container_end(source, start, group["last"], upper)
        if end <= start:
            start, end = lower, upper
        card = source[start:end]
        if _is_navigation_candidate(card):
            removed_navigation.append(group["id"])
            continue
        ranges.append((group["id"], start, end))
    return ranges, raw_count, len(groups), removed_navigation


def _ranges_with_diagnostics(source):
    article_ranges = previous.base._card_ranges(source)
    link_ranges, raw_link_count, unique_link_count, removed_navigation = _wide_link_ranges(source)
    if article_ranges:
        ranges = article_ranges
        strategy = "article_data_adid"
    else:
        ranges = link_ranges
        strategy = "s_anzeige_complete_container_windows"
    diagnostics = {
        "html_bytes": len(source),
        "html_article_tags": len(previous._ARTICLE_TAG_RE.findall(source)),
        "html_article_data_adid": len(previous.base._ARTICLE_RE.findall(source)),
        "html_all_data_adid": len(previous._DATA_ADID_RE.findall(source)),
        "html_s_anzeige_links": raw_link_count,
        "html_unique_s_anzeige_links": unique_link_count,
        "candidate_card_count": len(ranges),
        "article_candidate_count": len(article_ranges),
        "link_candidate_count_before_filter": unique_link_count,
        "link_candidate_count": len(link_ranges),
        "navigation_candidates_removed": len(removed_navigation),
        "navigation_candidate_ids": removed_navigation,
        "extraction_strategy": strategy,
        "container_strategy": "complete_li_or_article_else_next_unique_link",
    }
    return ranges, diagnostics


def _parse_explicit_price(card):
    candidates = []
    for match in _PRICE_CLASS_RE.finditer(card):
        candidates.append(previous.base._text(match.group(1)))
    candidates.append(card)
    for candidate in candidates:
        match = _EXPLICIT_EURO_RE.search(candidate)
        if not match:
            continue
        whole = match.group(1).replace(".", "")
        cents = match.group(2) or "0"
        try:
            return float(whole) + float(cents) / 100.0, match.group(0).strip(), "explicit_euro"
        except ValueError:
            pass
    match = _DATA_PRICE_RE.search(card)
    if match:
        raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(raw), f"{raw} €", "structured_price"
        except ValueError:
            pass
    return None, None, None


def _extract_card(source, listing_id, start, end, payload):
    item = previous.base._extract_card(source, listing_id, start, end, payload)
    if item is None:
        return None
    if str(item.get("title") or "").casefold().strip(" .:-") in _NAVIGATION_TITLES:
        return None
    if item.get("price") is None:
        price, price_raw, strategy = _parse_explicit_price(source[start:end])
        if price is not None:
            item["price"] = price
            item["price_raw"] = price_raw
            item["price_strategy"] = strategy
            evaluation = previous.base._evaluate(item, payload)
            item["traffic_light"] = evaluation
            item["score"] = evaluation["score"]
            item["decision"] = evaluation["decision"]
            item["match"] = {
                "score": evaluation["score"],
                "decision": evaluation["decision"],
                "listing_class": evaluation["label"],
                "reason": evaluation["reason"],
            }
    else:
        item["price_strategy"] = "legacy_price_class"
    return item


async def search_page(payload, fetch_html):
    original_ranges = previous._ranges_with_diagnostics
    original_extract = previous.base._extract_card
    previous._ranges_with_diagnostics = _ranges_with_diagnostics
    previous.base._extract_card = _extract_card
    try:
        result = await previous.search_page(payload, fetch_html)
    finally:
        previous._ranges_with_diagnostics = original_ranges
        previous.base._extract_card = original_extract

    pagination = result.get("pagination") or {}
    coverage = result.get("coverage_diagnostics") or {}
    listings = result.get("listings") or []
    source_page = int(pagination.get("source_page") or 0)
    packet_index = int(pagination.get("packet_index") or 0)
    source_cards = int(pagination.get("source_cards") or 0)
    selected_count = int(coverage.get("selected_range_count") or 0)
    consumed = min(source_cards, packet_index * PACKET_SIZE + selected_count)
    source_page_finished = consumed >= source_cards

    # Once a physical source page is finished, the next request must start at
    # packet zero of the following source page. This also handles short pages.
    if (
        not pagination.get("complete")
        and source_page_finished
        and pagination.get("cursor_url")
    ):
        pagination["next_page"] = (source_page + 1) * PACKETS_PER_SOURCE_PAGE
        pagination["cursor_transition"] = True
    else:
        pagination["cursor_transition"] = False

    recognized_prices = sum(item.get("price") is not None for item in listings)
    missing_prices = len(listings) - recognized_prices
    price_strategies = {}
    for item in listings:
        strategy = str(item.get("price_strategy") or "missing")
        price_strategies[strategy] = price_strategies.get(strategy, 0) + 1

    coverage.update({
        "schema": "direct-stdlib-cursor-price-diagnostics-v1",
        "price_recognized_count": recognized_prices,
        "price_missing_count": missing_prices,
        "price_strategy_counts": price_strategies,
        "source_page_finished": source_page_finished,
        "cursor_transition": bool(pagination.get("cursor_transition")),
        "cursor_next_page": pagination.get("next_page"),
        "cursor_url": pagination.get("cursor_url"),
        "diagnostic_event_required": True,
    })
    pagination["worker_unit"] = WORKER_UNIT
    result["pagination"] = pagination
    result["coverage_diagnostics"] = coverage
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": "worker_runtime_v04452",
        "cursor_pagination": True,
        "price_fallback": True,
        "diagnostic_events": True,
    }
    result["deployment_identity"] = identity()
    return result


def identity():
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "entrypoint": "cloudflare_worker.Default.fetch",
        "runtime_module": "worker_runtime_v04452",
        "worker_unit": WORKER_UNIT,
        "reference_version": "0.44.4",
        "technical_base": "0.44.5.1",
        "runtime_model": "direct-worker-stdlib-cursor-price-v1",
    }
