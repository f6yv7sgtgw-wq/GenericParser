"""Safe entry wrapper for the 0.44.5.2 lightweight runtime.

The implementation temporarily installs its extractor into the inherited
0.44.5.1 pipeline. This wrapper captures the unmodified base extractor before
that installation so the enhanced extractor cannot recurse into itself.
"""
from __future__ import annotations

import worker_runtime_v04452 as implementation

_ORIGINAL_EXTRACT_CARD = implementation.previous.base._extract_card


def _safe_extract_card(source, listing_id, start, end, payload):
    item = _ORIGINAL_EXTRACT_CARD(source, listing_id, start, end, payload)
    if item is None:
        return None
    if str(item.get("title") or "").casefold().strip(" .:-") in implementation._NAVIGATION_TITLES:
        return None
    if item.get("price") is None:
        price, price_raw, strategy = implementation._parse_explicit_price(source[start:end])
        if price is not None:
            item["price"] = price
            item["price_raw"] = price_raw
            item["price_strategy"] = strategy
            evaluation = implementation.previous.base._evaluate(item, payload)
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


implementation._extract_card = _safe_extract_card

VERSION = implementation.VERSION
BUILD_ID = implementation.BUILD_ID
API_CONTRACT = implementation.API_CONTRACT
WORKER_UNIT = implementation.WORKER_UNIT
PACKET_SIZE = implementation.PACKET_SIZE
PayloadError = implementation.PayloadError
UpstreamError = implementation.UpstreamError
ParserLayoutError = implementation.ParserLayoutError
SearchPayload = implementation.SearchPayload
search_page = implementation.search_page


def identity():
    data = implementation.identity()
    data["runtime_entry_module"] = "worker_runtime_v04452_entry"
    data["safe_extractor_binding"] = True
    return data
