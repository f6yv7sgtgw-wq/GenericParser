"""GenericParser 0.44.3 traffic-light evaluation.

Search, extraction, pagination and persistence remain inherited from reference 0.44.2.
Only result evaluation metadata is replaced by a deterministic red/yellow/green model.
"""
from __future__ import annotations
import re
from typing import Any
from fastapi import Request
from . import search_service_v0442 as previous
from .build_identity_v0443 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = previous.SearchRequest

_STOP = {"der", "die", "das", "ein", "eine", "und", "oder", "mit", "für", "von", "neu", "ovp"}

def _terms(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    return [str(item).strip().lower() for item in value if str(item).strip()]

def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9äöüß]+", value.lower()) if len(token) > 1 and token not in _STOP]

def _criterion(name: str, color: str, reason: str, hard: bool = False) -> dict[str, Any]:
    return {"name": name, "color": color, "reason": reason, "hard": hard}

def _evaluate(listing: dict[str, Any], payload: SearchRequest) -> dict[str, Any]:
    title = str(listing.get("title") or "")
    haystack = title.lower()
    info = listing.get("result_info") if isinstance(listing.get("result_info"), dict) else {}
    offer_type = str(info.get("offer_type") or "Produkt")
    condition = str(info.get("condition") or "Zustand offen")
    scope = str(info.get("scope") or "Einzelangebot")

    required = _terms(getattr(payload, "required_terms", None))
    excluded = _terms(getattr(payload, "excluded_terms", None))
    required_ok = all(term in haystack for term in required) if required else True
    excluded_ok = not any(term in haystack for term in excluded)
    if required_ok and excluded_ok:
        term_color, term_reason = "green", "Pflichtbegriffe erfüllt · keine Ausschlussbegriffe"
    elif required_ok or excluded_ok:
        term_color = "yellow"
        term_reason = "Nur eine Begriffsbedingung erfüllt"
    else:
        term_color, term_reason = "red", "Pflichtbegriffe fehlen · Ausschlussbegriff erkannt"
    criteria = [_criterion("Begriffe", term_color, term_reason, not excluded_ok)]

    query_tokens = _tokens(str(getattr(payload, "query", "") or ""))
    title_tokens = set(_tokens(title))
    matched = sum(token in title_tokens for token in query_tokens)
    ratio = matched / len(query_tokens) if query_tokens else 1.0
    if ratio >= 0.75:
        criteria.append(_criterion("Suchbegriff", "green", "Suchbegriff eindeutig erkannt"))
    elif ratio >= 0.4:
        criteria.append(_criterion("Suchbegriff", "yellow", "Suchbegriff teilweise erkannt"))
    else:
        criteria.append(_criterion("Suchbegriff", "red", "Kein belastbarer Bezug zum Suchbegriff", True))

    wanted = offer_type == "Gesuch"
    accessory = offer_type == "Zubehör"
    if wanted:
        criteria.append(_criterion("Verkaufsangebot", "red", "Gesuch statt Verkaufsangebot", True))
    elif accessory:
        criteria.append(_criterion("Angebotsart", "red", "Zubehör statt gesuchtem Produkt", True))
    elif offer_type in {"Spiel/Cartridge", "Konsole/Handheld"}:
        criteria.append(_criterion("Angebotsart", "green", offer_type))
    else:
        criteria.append(_criterion("Angebotsart", "yellow", "Produktart nicht eindeutig"))

    accept_incomplete = bool(getattr(payload, "accept_incomplete", False))
    defective = condition == "defekt/unvollständig"
    if defective and not accept_incomplete:
        criteria.append(_criterion("Zustand", "red", "Defekt oder unvollständig nicht akzeptiert", True))
    elif condition == "Zustand offen":
        criteria.append(_criterion("Zustand", "yellow", "Zustand nicht angegeben"))
    else:
        criteria.append(_criterion("Zustand", "green", condition))

    accept_bundles = bool(getattr(payload, "accept_bundles", False))
    is_bundle = scope == "Bundle"
    if is_bundle and not accept_bundles:
        criteria.append(_criterion("Umfang", "red", "Bundle ist ausgeschlossen", True))
    else:
        criteria.append(_criterion("Umfang", "green", scope))

    price = listing.get("price")
    try:
        price_value = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_value = None
    max_price = getattr(payload, "max_price", None)
    market_value = getattr(payload, "market_value", None)
    if max_price is not None:
        if price_value is None:
            criteria.append(_criterion("Maximalpreis", "yellow", "Preis fehlt oder ist VB"))
        elif price_value <= float(max_price):
            criteria.append(_criterion("Maximalpreis", "green", "Innerhalb des Maximalpreises"))
        else:
            criteria.append(_criterion("Maximalpreis", "red", "Über dem Maximalpreis", True))
    if market_value is not None:
        if price_value is None:
            criteria.append(_criterion("Richtwert", "yellow", "Kein belastbarer Preis"))
        elif price_value <= float(market_value):
            criteria.append(_criterion("Richtwert", "green", "Auf oder unter dem Richtwert"))
        elif price_value <= float(market_value) * 1.2:
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
        reasons = ["Alle geprüften Bedingungen erfüllt"]
    return {
        "color": color,
        "label": label,
        "criteria": criteria,
        "reason": " · ".join(reasons[:3]),
        "score": score,
        "decision": decision,
    }

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await previous.search_page(payload, request)
    counts = {"green": 0, "yellow": 0, "red": 0}
    for listing in result.get("listings") or []:
        evaluation = _evaluate(listing, payload)
        counts[evaluation["color"]] += 1
        listing["traffic_light"] = evaluation
        listing["match"] = {
            **(listing.get("match") if isinstance(listing.get("match"), dict) else {}),
            "listing_class": evaluation["label"],
            "score": evaluation["score"],
            "decision": evaluation["decision"],
            "reason": evaluation["reason"],
        }
    result["traffic_light_summary"] = counts
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "reference_version": "0.44.2",
        "traffic_light_model": "v1",
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
        "reference_version": "0.44.2",
    }
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
