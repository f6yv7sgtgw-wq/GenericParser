"""Deferred Vinted detail enrichment introduced in GenericParser 1.3.2.

This module is deliberately outside the protected multi-source pagination path.
It enriches one already returned browser batch, merges the new fields into the
existing listings and re-evaluates price-dependent matching rules.
"""
from __future__ import annotations

from typing import Any

from . import search_service_v0444 as reference
from .product_classification import (
    apply_classification_evaluation,
    apply_classification_metadata,
    classify_listing,
)
from .vinted_adapter import DETAIL_BATCH_LIMIT, enrich_vinted_details


_DETAIL_FIELDS = ("image", "price", "description", "condition", "size")


def _detail_fields(listing: dict[str, Any]) -> list[str]:
    fields = listing.get("detail_enrichment")
    fields = fields.get("fields") if isinstance(fields, dict) else []
    return [str(value) for value in fields] if isinstance(fields, list) else []


def _merge_listing(original: dict[str, Any], enriched: dict[str, Any]) -> dict[str, Any]:
    merged = dict(original)
    for key in ("title", "url", "image_url", "price", "price_raw", "description", "place"):
        value = enriched.get(key)
        if value is not None and value != "":
            merged[key] = value

    detail = enriched.get("detail_enrichment") if isinstance(enriched.get("detail_enrichment"), dict) else {}
    fields = _detail_fields(enriched)
    original_info = original.get("result_info") if isinstance(original.get("result_info"), dict) else {}
    enriched_info = enriched.get("result_info") if isinstance(enriched.get("result_info"), dict) else {}
    merged_info = {**original_info}
    for key in ("offer_type", "scope", "fit"):
        if enriched_info.get(key):
            merged_info[key] = enriched_info[key]
    if "condition" in fields:
        merged_info["condition"] = enriched_info.get("condition")
        if enriched_info.get("display_text"):
            merged_info["display_text"] = enriched_info["display_text"]
    # A detail page only overrides the catalog size when it actually carries one;
    # a missing size must not erase what the catalog already delivered.
    if "size" in fields and enriched_info.get("size"):
        merged_info["size"] = enriched_info["size"]
        if enriched_info.get("display_text"):
            merged_info["display_text"] = enriched_info["display_text"]
    merged["result_info"] = merged_info
    merged["detail_enrichment"] = {
        "status": str(detail.get("status") or "empty"),
        "fields": fields,
        "mode": "background-batch",
    }
    merged["source"] = "vinted"
    merged["source_label"] = "Vinted"
    return merged


def _decorate(listing: dict[str, Any], payload: Any) -> dict[str, Any]:
    classification = classify_listing(listing, str(payload.query))
    apply_classification_metadata(listing, classification)
    evaluation = reference._evaluate(listing, payload)
    evaluation = apply_classification_evaluation(evaluation, classification)
    listing["traffic_light"] = evaluation
    listing["match"] = {
        "listing_class": evaluation["label"],
        "score": evaluation["score"],
        "decision": evaluation["decision"],
        "reason": evaluation["reason"],
    }
    return listing


def _has_complete_details(listing: dict[str, Any]) -> bool:
    return bool(listing.get("image_url") and listing.get("price") is not None and listing.get("description"))


async def enrich_vinted_batch(listings: list[dict[str, Any]], payload: Any) -> dict[str, Any]:
    if not isinstance(listings, list) or not listings:
        raise ValueError("Vinted detail batch requires at least one listing")
    if len(listings) > DETAIL_BATCH_LIMIT:
        raise ValueError(f"Vinted detail batch exceeds limit {DETAIL_BATCH_LIMIT}")
    for listing in listings:
        if not isinstance(listing, dict) or not str(listing.get("id") or "").startswith("vinted:"):
            raise ValueError("Vinted detail batch accepts Vinted listings only")

    service = await enrich_vinted_details(listings)
    enriched_by_id = {
        str(item.get("id")): item
        for item in service.get("listings") or []
        if isinstance(item, dict) and item.get("id")
    }
    output: list[dict[str, Any]] = []
    complete = partial = failed = 0
    for original in listings:
        listing_id = str(original.get("id") or "")
        enriched = enriched_by_id.get(listing_id)
        if enriched is None:
            merged = dict(original)
            existing_fields = _detail_fields(original)
            merged["detail_enrichment"] = {
                "status": "background_error",
                "fields": existing_fields,
                "mode": "background-batch",
                "reason": service.get("reason") or "detail_response_missing",
            }
        else:
            merged = _merge_listing(original, enriched)
        merged = _decorate(merged, payload)
        output.append(merged)
        if _has_complete_details(merged):
            complete += 1
        elif str((merged.get("detail_enrichment") or {}).get("status")) in {"background_error", "error", "blocked", "empty"}:
            failed += 1
        else:
            partial += 1

    return {
        "status": "ok",
        "mode": "background-batch",
        "strategy": service.get("strategy") or "service-binding-deferred-detail",
        "service_status": service.get("status"),
        "service_reason": service.get("reason"),
        "detail_batch_limit": DETAIL_BATCH_LIMIT,
        "requested": len(listings),
        "complete": complete,
        "partial": partial,
        "failed": failed,
        "fields": list(_DETAIL_FIELDS),
        "elapsed_ms": service.get("elapsed_ms"),
        "listings": output,
    }


__all__ = ["DETAIL_BATCH_LIMIT", "enrich_vinted_batch"]
