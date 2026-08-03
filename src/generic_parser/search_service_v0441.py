"""GenericParser 0.44.1 stability search service.

The complete search, extraction, title recovery, pagination, stop/resume and
semantic card data come from the proven 0.43.6.3 implementation. This release
only adds presentation labels required by the 0.44 card UI.
"""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v04363 as stable
from .build_identity_v0441 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = stable.SearchRequest

_LABELS = {
    "passend": ("Sehr guter Treffer", "good"),
    "prüfen": ("Prüfen", "review"),
    "wahrscheinlich unpassend": ("Eher unpassend", "bad"),
    "kein Verkaufsangebot": ("Kein Verkaufsangebot", "bad"),
}


def _presentation(info: dict[str, Any]) -> dict[str, Any]:
    fit = str(info.get("fit") or "prüfen")
    label, tone = _LABELS.get(fit, ("Prüfen", "review"))
    parts = [str(info.get("offer_type") or "Produkt")]
    condition = str(info.get("condition") or "")
    if condition and condition != "Zustand offen":
        parts.append(condition)
    scope = str(info.get("scope") or "")
    if scope:
        parts.append(scope)
    return {
        **info,
        "fit_label": label,
        "fit_tone": tone,
        "compact_details": " · ".join(parts),
    }


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await stable.search_page(payload, request)
    for listing in result.get("listings") or []:
        info = listing.get("result_info") if isinstance(listing.get("result_info"), dict) else {}
        listing["result_info"] = _presentation(info)
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "stable_base": "0.43.6.3",
        "optimized_result_cards": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
