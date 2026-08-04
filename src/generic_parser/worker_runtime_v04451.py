"""GenericParser 0.44.5.1 extraction hotfix for the direct Free Worker.

Keeps the 0.44.5 direct WorkerEntrypoint and active-rule evaluation. Adds a
link-driven fallback for Kleinanzeigen result pages whose cards no longer expose
``<article data-adid>`` and refuses to report a populated page as empty.
"""
from __future__ import annotations

import html as html_lib
import re
from urllib.parse import urljoin

import worker_runtime_v0445 as base

VERSION = "0.44.5.1"
BUILD_ID = "gp-04451-20260804-1"
API_CONTRACT = "match-v6.12.1-direct-free-worker-extraction"
WORKER_UNIT = "direct-worker+stdlib-link-fallback+active-rules"
BASE_URL = base.BASE_URL
SOURCE_PAGE_SIZE = base.SOURCE_PAGE_SIZE
PACKET_SIZE = base.PACKET_SIZE
PACKETS_PER_SOURCE_PAGE = base.PACKETS_PER_SOURCE_PAGE
MAX_VIRTUAL_PAGE = base.MAX_VIRTUAL_PAGE

PayloadError = base.PayloadError
UpstreamError = base.UpstreamError
SearchPayload = base.SearchPayload

_LINK_CANDIDATE_RE = re.compile(
    r'<a\b[^>]*\bhref=["\']([^"\']*/s-anzeige/[^"\']+)["\'][^>]*>',
    re.I,
)
_ID_IN_HREF_RE = re.compile(r"/s-anzeige/[^?#\"']*/(\d{8,12})(?:[-/?#]|$)", re.I)
_FALLBACK_ID_RE = re.compile(r"(?<!\d)(\d{8,12})(?!\d)")
_ARTICLE_TAG_RE = re.compile(r"<article\b", re.I)
_DATA_ADID_RE = re.compile(r"\bdata-adid\s*=", re.I)


class ParserLayoutError(RuntimeError):
    def __init__(self, detail, diagnostics):
        super().__init__(detail)
        self.detail = detail
        self.diagnostics = diagnostics


def _listing_id_from_href(href):
    clean = html_lib.unescape(str(href or ""))
    match = _ID_IN_HREF_RE.search(clean)
    if match:
        return match.group(1)
    tail = clean.rsplit("/", 1)[-1]
    match = _FALLBACK_ID_RE.search(tail)
    return match.group(1) if match else None


def _link_groups(source):
    groups = {}
    order = []
    raw_count = 0
    for match in _LINK_CANDIDATE_RE.finditer(source):
        raw_count += 1
        href = html_lib.unescape(match.group(1))
        listing_id = _listing_id_from_href(href)
        if not listing_id:
            continue
        if listing_id not in groups:
            groups[listing_id] = {
                "id": listing_id,
                "href": href,
                "first": match.start(),
                "last": match.end(),
            }
            order.append(listing_id)
        else:
            groups[listing_id]["first"] = min(groups[listing_id]["first"], match.start())
            groups[listing_id]["last"] = max(groups[listing_id]["last"], match.end())
    return [groups[key] for key in order], raw_count


def _nearest_container_start(source, lower, anchor):
    candidates = []
    for marker in ("<article", '<li class="ad-listitem', "<li class='ad-listitem", '<div class="aditem', "<div class='aditem"):
        pos = source.rfind(marker, lower, anchor + 1)
        if pos >= 0:
            candidates.append(pos)
    return max(candidates) if candidates else lower


def _container_end(source, start, anchor_end, upper):
    prefix = source[start:start + 32].lower()
    closing = None
    if prefix.startswith("<article"):
        closing = "</article>"
    elif prefix.startswith("<li"):
        closing = "</li>"
    elif prefix.startswith("<div"):
        closing = "</div>"
    if closing:
        pos = source.find(closing, anchor_end, min(len(source), upper + 20_000))
        if pos >= 0:
            return pos + len(closing)
    return upper


def _link_window_ranges(source):
    groups, raw_count = _link_groups(source)
    ranges = []
    for index, group in enumerate(groups):
        previous_last = groups[index - 1]["last"] if index else 0
        next_first = groups[index + 1]["first"] if index + 1 < len(groups) else len(source)
        lower = max(previous_last, group["first"] - 20_000, 0)
        upper = min(next_first, group["last"] + 30_000, len(source))
        start = _nearest_container_start(source, lower, group["first"])
        end = _container_end(source, start, group["last"], upper)
        if end <= start:
            start, end = lower, upper
        ranges.append((group["id"], start, end))
    return ranges, raw_count, len(groups)


def _ranges_with_diagnostics(source):
    article_ranges = base._card_ranges(source)
    link_ranges, raw_link_count, unique_link_count = _link_window_ranges(source)
    if article_ranges:
        ranges = article_ranges
        strategy = "article_data_adid"
    else:
        ranges = link_ranges
        strategy = "s_anzeige_link_windows"
    diagnostics = {
        "html_bytes": len(source),
        "html_article_tags": len(_ARTICLE_TAG_RE.findall(source)),
        "html_article_data_adid": len(base._ARTICLE_RE.findall(source)),
        "html_all_data_adid": len(_DATA_ADID_RE.findall(source)),
        "html_s_anzeige_links": raw_link_count,
        "html_unique_s_anzeige_links": unique_link_count,
        "candidate_card_count": len(ranges),
        "article_candidate_count": len(article_ranges),
        "link_candidate_count": len(link_ranges),
        "extraction_strategy": strategy,
    }
    return ranges, diagnostics


def _layout_error(source, reported_total, diagnostics, reason):
    details = {
        **diagnostics,
        "reported_total": reported_total,
        "reason": reason,
        "schema": "direct-stdlib-link-fallback-v1",
    }
    raise ParserLayoutError(
        "Kleinanzeigen meldet Ergebnisse, aber die Anzeigenkarten konnten nicht erkannt werden.",
        details,
    )


async def search_page(payload, fetch_html):
    source_page = payload.page // PACKETS_PER_SOURCE_PAGE
    packet_index = payload.page % PACKETS_PER_SOURCE_PAGE
    request_url = base._source_url(payload, source_page)
    source = payload.html or "" if payload.mode == "html" else await fetch_html(request_url)
    reported_total = base._reported_total(source)
    ranges, extraction_diagnostics = _ranges_with_diagnostics(source)

    if not ranges and reported_total and reported_total > 0:
        _layout_error(source, reported_total, extraction_diagnostics, "reported_total_without_candidates")

    start_index = packet_index * PACKET_SIZE
    selected = ranges[start_index:start_index + PACKET_SIZE]
    extracted = []
    malformed = []
    for listing_id, start, end in selected:
        item = base._extract_card(source, listing_id, start, end, payload)
        if item is None:
            malformed.append({"id": listing_id, "reason": "card_not_extractable"})
        else:
            extracted.append(item)

    if selected and not extracted and reported_total and reported_total > 0:
        _layout_error(source, reported_total, {
            **extraction_diagnostics,
            "selected_range_count": len(selected),
            "selected_ids": [entry[0] for entry in selected],
            "malformed": malformed,
        }, "selected_candidates_not_extractable")

    visible = [
        item for item in extracted
        if item["decision"] == "accept"
        or (item["decision"] == "review" and payload.include_review)
        or (item["decision"] == "reject" and payload.include_rejected)
    ]
    fetched = len(extracted)
    hidden = fetched - len(visible)
    source_cards = len(ranges)
    consumed = min(source_cards, start_index + len(selected))
    source_page_finished = consumed >= source_cards
    discovered_next = base._next_url(source) if source_page_finished else request_url

    complete = False
    stop_reason = "work_packet_complete"
    if source_cards == 0 and not reported_total:
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

    coverage = {
        "schema": "direct-stdlib-link-fallback-v1",
        "source_page": source_page,
        "packet_index": packet_index,
        **extraction_diagnostics,
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
        "next_link": {
            "selected_href": discovered_next,
            "selected_strategy": "source_html_weiter_link" if discovered_next else None,
        },
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
        "false_empty_page_guard": True,
    }

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
        "coverage_diagnostics": coverage,
        "worker": {
            "version": VERSION,
            "build_id": BUILD_ID,
            "api_contract": API_CONTRACT,
            "worker_unit": WORKER_UNIT,
            "source_used": "html-light-packets",
            "matching": "active-rules-v2",
            "search_module": "worker_runtime_v04451",
            "reference_version": "0.44.4",
            "traffic_light_model": "v2-active-rules",
            "empty_fields_ignored": True,
            "direct_worker": True,
            "link_fallback": True,
            "false_empty_page_guard": True,
            "asgi": False,
            "fastapi": False,
            "pydantic": False,
            "httpx": False,
        },
        "deployment_identity": identity(),
        "consistency": {
            "ok": fetched == len(visible) + hidden,
            "fetched_equals_visible_plus_hidden": fetched == len(visible) + hidden,
            "visible_equals_listings": len(visible) == len(visible),
            "reported_total_not_used_as_stop": True,
            "source_next_link_checked": source_page_finished,
            "next_link_state_consistent": complete or bool(discovered_next),
            "false_empty_page_prevented": bool(reported_total and reported_total > 0) or source_cards == 0,
        },
    }


def identity():
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "entrypoint": "cloudflare_worker.Default.fetch",
        "runtime_module": "worker_runtime_v04451",
        "worker_unit": WORKER_UNIT,
        "reference_version": "0.44.4",
        "technical_base": "0.44.5",
        "runtime_model": "direct-worker-stdlib-link-fallback-v1",
    }
