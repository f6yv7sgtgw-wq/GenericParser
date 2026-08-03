"""GenericParser 0.44.4 active-rule traffic-light evaluation.

Search, extraction, pagination and persistence remain inherited unchanged from
reference 0.44.2. Empty fields and disabled options are not evaluated.
"""
from __future__ import annotations
import re
from typing import Any
from fastapi import Request
from . import search_service_v0442 as previous
from .build_identity_v0444 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

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
    return {"name": name, "color": color, "reason": reason, "hard": hard, "active": True}


def _evaluate(listing: dict[str, Any], payload: SearchRequest) -> dict[str, Any]:
    title = str(listing.get("title") or "")
    haystack = title.lower()
    info = listing.get("result_info") if isinstance(listing.get("result_info"), dict) else {}
    offer_type = str(info.get("offer_type") or "Produkt")
    condition = str(info.get("condition") or "Zustand offen")
    scope = str(info.get("scope") or "Einzelangebot")
    criteria: list[dict[str, Any]] = []

    # Der Suchbegriff ist das einzige immer aktive Kriterium.
    query_tokens = _tokens(str(getattr(payload, "query", "") or ""))
    title_tokens = set(_tokens(title))
    matched = sum(token in title_tokens for token in query_tokens)
    ratio = matched / len(query_tokens) if query_tokens else 1.0
    if ratio >= 0.75:
        criteria.append(_criterion("Suchbegriff", "green", "Suchbegriff gefunden"))
    elif ratio >= 0.4:
        criteria.append(_criterion("Suchbegriff", "yellow", "Suchbegriff teilweise erkannt"))
    else:
        criteria.append(_criterion("Suchbegriff", "red", "Kein belastbarer Bezug zum Suchbegriff", True))

    # Pflicht- und Ausschlussbegriffe werden unabhängig nur bei Inhalt bewertet.
    required = _terms(getattr(payload, "required_terms", None))
    if required:
        missing = [term for term in required if term not in haystack]
        if missing:
            criteria.append(_criterion("Pflichtbegriffe", "red", "Pflichtbegriff fehlt", True))
        else:
            criteria.append(_criterion("Pflichtbegriffe", "green", "Pflichtbegriffe erfüllt"))

    excluded = _terms(getattr(payload, "excluded_terms", None))
    if excluded:
        found = [term for term in excluded if term in haystack]
        if found:
            criteria.append(_criterion("Ausschlussbegriffe", "red", "Ausschlussbegriff erkannt", True))
        else:
            criteria.append(_criterion("Ausschlussbegriffe", "green", "Keine Ausschlussbegriffe"))

    model_patterns = _terms(getattr(payload, "model_patterns", None))
    if model_patterns:
        if any(term in haystack for term in model_patterns):
            criteria.append(_criterion("Modellvarianten", "green", "Modell oder Schreibvariante erkannt"))
        else:
            criteria.append(_criterion("Modellvarianten", "yellow", "Modell oder Schreibvariante nicht erkannt"))

    brands = _terms(getattr(payload, "brands", None))
    if brands:
        if any(term in haystack for term in brands):
            criteria.append(_criterion("Marke", "green", "Marke erkannt"))
        else:
            criteria.append(_criterion("Marke", "yellow", "Marke nicht eindeutig erkannt"))

    # Ein Gesuch ist unabhängig von optionalen Feldern kein Verkaufsangebot.
    if offer_type == "Gesuch":
        criteria.append(_criterion("Verkaufsangebot", "red", "Gesuch statt Verkaufsangebot", True))

    # Zustand wird nur bei einer tatsächlich erkannten Unvollständigkeit bewertet.
    accept_incomplete = bool(getattr(payload, "accept_incomplete", False))
    if condition == "defekt/unvollständig" and not accept_incomplete:
        criteria.append(_criterion("Zustand", "red", "Defekt oder unvollständig nicht akzeptiert", True))
    elif condition == "defekt/unvollständig" and accept_incomplete:
        criteria.append(_criterion("Zustand", "green", "Unvollständige Angebote sind erlaubt"))

    # Die deaktivierte Bundle-Option ist eine aktive Ausschlussregel.
    accept_bundles = bool(getattr(payload, "accept_bundles", False))
    if scope == "Bundle":
        if accept_bundles:
            criteria.append(_criterion("Umfang", "green", "Bundle erlaubt"))
        else:
            criteria.append(_criterion("Umfang", "red", "Bundle ist ausgeschlossen", True))

    price = listing.get("price")
    try:
        price_value = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_value = None

    max_price = getattr(payload, "max_price", None)
    if max_price is not None:
        if price_value is None:
            criteria.append(_criterion("Maximalpreis", "yellow", "Preis fehlt oder ist VB"))
        elif price_value <= float(max_price):
            criteria.append(_criterion("Maximalpreis", "green", "Innerhalb des Maximalpreises"))
        else:
            criteria.append(_criterion("Maximalpreis", "red", "Über dem Maximalpreis", True))

    market_value = getattr(payload, "market_value", None)
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
        green_reasons = [item["reason"] for item in criteria if item["color"] == "green"]
        reasons = green_reasons[:2] or ["Alle aktiven Regeln erfüllt"]
    return {
        "color": color,
        "label": label,
        "criteria": criteria,
        "active_criteria": len(criteria),
        "reason": " · ".join(reasons[:3]),
        "score": score,
        "decision": decision,
    }


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await previous.search_page(payload, request)
    counts = {"green": 0, "yellow": 0, "red": 0}
    active_rule_counts: dict[str, int] = {}
    for listing in result.get("listings") or []:
        evaluation = _evaluate(listing, payload)
        counts[evaluation["color"]] += 1
        for criterion in evaluation["criteria"]:
            active_rule_counts[criterion["name"]] = active_rule_counts.get(criterion["name"], 0) + 1
        listing["traffic_light"] = evaluation
        listing["match"] = {
            **(listing.get("match") if isinstance(listing.get("match"), dict) else {}),
            "listing_class": evaluation["label"],
            "score": evaluation["score"],
            "decision": evaluation["decision"],
            "reason": evaluation["reason"],
        }
    result["traffic_light_summary"] = counts
    result["active_rule_summary"] = active_rule_counts
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "reference_version": "0.44.2",
        "traffic_light_model": "v2-active-rules",
        "empty_fields_ignored": True,
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
