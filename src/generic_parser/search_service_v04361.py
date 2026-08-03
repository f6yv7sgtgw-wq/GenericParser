"""GenericParser 0.43.6.1 diagnostic alignment and useful result information.

Based on the proven 0.43.6 flow. Search, pagination and CPU work packets remain
unchanged. This patch removes false title_empty diagnostics for successfully
recovered cards and replaces the generic Free-plan reason with concrete card
information.
"""
from __future__ import annotations

from typing import Any
from fastapi import Request

from . import search_service_v0436 as flow
from .build_identity_v04361 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = flow.SearchRequest


def _offer_type(title: str, description: str | None) -> str:
    text = f"{title} {description or ''}".casefold()
    if any(term in text for term in ("suche ", "gesucht", "kaufe ", "ankauf")):
        return "Gesuch"
    if any(term in text for term in ("sammlung", "paket", "bundle", "konvolut", "mehrere spiele", "cartridges", "module")):
        return "Bundle/Sammlung"
    if any(term in text for term in ("konsole", "handheld", "super pocket", "superpocket", "evercade vs", "evercade exp")):
        return "Konsole/Handheld"
    if any(term in text for term in ("grip", "tasche", "kabel", "netzteil", "halter", "case", "zubehör")):
        return "Zubehör"
    if any(term in text for term in ("cartridge", "collection", "arcade", "museum", "lynx", "piko", "namco", "irem", "toaplan", "turrican")):
        return "Cartridge"
    return "Sonstiges"


def _information_reason(item: dict[str, Any]) -> str:
    offer_type = _offer_type(str(item.get("title") or ""), item.get("description"))
    strategy = str(item.get("title_strategy") or "unbekannt")
    listing_id = str(item.get("id") or "–")
    return f"{offer_type} · Titel: {strategy} · Anzeige {listing_id}"


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await flow.search_page(payload, request)

    listings = result.get("listings") or []
    for item in listings:
        offer_type = _offer_type(str(item.get("title") or ""), item.get("description"))
        item["offer_type"] = offer_type
        item["information"] = {
            "offer_type": offer_type,
            "title_strategy": item.get("title_strategy"),
            "listing_id": item.get("id"),
        }
        match = item.get("match") or {}
        match["reason"] = _information_reason(item)
        item["match"] = match

    diagnostics = result.get("coverage_diagnostics") or {}
    returned_ids = {str(value) for value in diagnostics.get("returned_ids") or []}
    old_malformed = diagnostics.get("malformed") or []
    recovered = [entry for entry in old_malformed if str(entry.get("id")) in returned_ids]
    unresolved = [entry for entry in old_malformed if str(entry.get("id")) not in returned_ids]
    diagnostics.update({
        "schema": "robust-title-info-v1",
        "malformed": unresolved,
        "malformed_count": len(unresolved),
        "title_empty_count": sum(entry.get("reason") == "title_empty" for entry in unresolved),
        "anzeige_link_missing_count": sum(entry.get("reason") == "anzeige_link_missing" for entry in unresolved),
        "recovered_title_count": len(recovered),
        "recovered_titles": [
            {"id": entry.get("id"), "title_strategy": next((item.get("title_strategy") for item in listings if str(item.get("id")) == str(entry.get("id"))), None)}
            for entry in recovered
        ],
        "diagnostic_uses_final_extraction_result": True,
        "result_information_active": True,
    })
    result["coverage_diagnostics"] = diagnostics
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "result_information": True,
        "diagnostic_alignment": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result


__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
