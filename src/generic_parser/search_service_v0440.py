"""GenericParser 0.44.0 presentation optimization.

The proven 0.43.6.3 search, extraction, pagination and semantic classification
remain unchanged. This release only adds presentation labels used by the UI.
"""
from __future__ import annotations
from typing import Any
from fastapi import Request
from . import search_service_v04363 as previous
from .build_identity_v0440 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = previous.SearchRequest

_FIT_LABELS = {
    "passend": ("Sehr guter Treffer", "good"),
    "prüfen": ("Prüfen", "review"),
    "wahrscheinlich unpassend": ("Eher unpassend", "bad"),
    "kein Verkaufsangebot": ("Kein Verkaufsangebot", "bad"),
}

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await previous.search_page(payload, request)
    for listing in result.get("listings") or []:
        info = listing.get("result_info") if isinstance(listing.get("result_info"), dict) else {}
        fit = str(info.get("fit") or "prüfen")
        label, tone = _FIT_LABELS.get(fit, ("Prüfen", "review"))
        condition = str(info.get("condition") or "Zustand offen")
        scope = str(info.get("scope") or "Einzelangebot")
        offer_type = str(info.get("offer_type") or "Produkt")
        details = [offer_type, scope]
        if condition != "Zustand offen":
            details.insert(1, condition)
        info.update({
            "fit_label": label,
            "fit_tone": tone,
            "compact_details": " · ".join(details),
        })
        listing["result_info"] = info

    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
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
