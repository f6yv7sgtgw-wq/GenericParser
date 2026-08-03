"""GenericParser 0.43.6.3 semantic result-card enrichment.

Search, extraction, pagination and diagnostics remain inherited from 0.43.6.2.
Only the user-facing card information is replaced with meaningful attributes.
"""
from __future__ import annotations
import re
from typing import Any
from fastapi import Request
from . import search_service_v04362 as previous
from .build_identity_v04363 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, WORKER_UNIT

SearchRequest = previous.SearchRequest

_WANTED = re.compile(r"\b(suche|gesucht|suche nach|ankauf|kaufe)\b", re.I)
_ACCESSORY = re.compile(r"\b(lenkrad|tasche|case|hülle|halter|grip|sticker|pin[- ]?set|figur|rennstrecke|carrera|hot wheels|k'nex|klemmbaustein|kartenspiel|merch|controller|kabel|netzteil)\b", re.I)
_CONSOLE = re.compile(r"\b(konsole|handheld|switch oled|switch v2|switch lite|evercade exp|evercade vs|super pocket|bartop)\b", re.I)
_BUNDLE = re.compile(r"\b(bundle|paket|set|sammlung|konvolut|inkl\.?|plus|mit \d+|\d+ spiele|mehrere|komplett)\b|\+", re.I)
_GAME = re.compile(r"\b(spiel|game|cartridge|cardridge|cartrid|collection|arcade|modul|module)\b", re.I)
_NEW = re.compile(r"\b(neu|ovp|originalverpackt|versiegelt|sealed|ungeöffnet|in folie)\b", re.I)
_LIKE_NEW = re.compile(r"\b(wie neu|neuwertig|top zustand|sehr gut)\b", re.I)
_DEFECT = re.compile(r"\b(defekt|kaputt|beschädigt|akku defekt|unvollständig)\b", re.I)
_USED = re.compile(r"\b(gebraucht|gut erhalten|guter zustand)\b", re.I)
_STOP = {"neu", "ovp", "und", "mit", "für", "der", "die", "das", "ein", "eine", "inkl", "original", "verpackt"}

def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in _STOP]

def _card_info(title: str, query: str) -> dict[str, str]:
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

async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    result = await previous.search_page(payload, request)
    for listing in result.get("listings") or []:
        info = _card_info(str(listing.get("title") or ""), str(payload.query or ""))
        listing["result_info"] = info
        match = listing.get("match") if isinstance(listing.get("match"), dict) else {}
        listing["match"] = {**match, "reason": info["display_text"]}
    result["worker"] = {
        **(result.get("worker") or {}),
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "semantic_result_cards": True,
    }
    result["deployment_identity"] = {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "search_module": SEARCH_MODULE,
    }
    return result

__all__ = ["SearchRequest", "search_page", "VERSION", "BUILD_ID", "API_CONTRACT"]
