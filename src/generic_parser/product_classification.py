"""Deterministic product classification for marketplace search results.

The classifier is deliberately explainable and source independent.  It uses
only public listing/category text and never stores seller or account data.
Project-specific Evercade and SNES signals are part of the shared rules so the
same result contract can be consumed by both collection managers.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


CLASS_LABELS = {
    "main_product": "Hauptprodukt",
    "accessory_part": "Zubehör/Ersatzteil",
    "bundle": "Bundle/Konvolut",
    "wanted": "Gesuch",
    "rental": "Vermietung",
    "service": "Dienstleistung",
    "related_merchandise": "Merchandise/anderes Produkt",
    "unknown": "Produktart offen",
}


_WANTED = (
    "ich suche",
    "suche ",
    "suche dringend",
    "gesucht",
    "ankauf",
    "kaufe an",
    "wanted",
)
_RENTAL = ("vermietung", "zu vermieten", "mietangebot", "verleih", "rent service")
_SERVICE = (
    "reparaturservice",
    "reparatur dienstleistung",
    "repariere",
    "modding service",
    "umbau service",
    "installation service",
)
_BUNDLE = (
    "konvolut",
    "spielepaket",
    "game lot",
    "games lot",
    "cartridge lot",
    "modul lot",
    "bundle",
    "komplettpaket",
)
_ACCESSORY = (
    "leerhülle",
    "leere hülle",
    "hülle ohne spiel",
    "box only",
    "case only",
    "cover only",
    "manual only",
    "nur anleitung",
    "nur spielanleitung",
    "nur handbuch",
    "nur das handbuch",
    "notice seule",
    "ohne spiel",
    "ohne modul",
    "ersatzhülle",
    "replacement case",
    "replacement shell",
    "cartridge shell",
    "schutzhülle",
    "schutzfolie",
    "dust cover",
    "display stand",
    "aufsteller",
    "controller",
    "gamepad",
    "joystick",
    "adapter",
    "netzteil",
    "kabel",
    "ersatzteil",
    "gehäuse",
    "anleitung einzeln",
    "manual einzeln",
    "label only",
)
_MERCHANDISE = (
    "kartenspiel",
    "brettspiel",
    "gesellschaftsspiel",
    "spielzeug",
    "actionfigur",
    "action figure",
    "sammelfigur",
    "figur",
    "amiibo",
    "jakks",
    "carrera",
    "pull & speed",
    "pull and speed",
    "hot wheels",
    "lego",
    "plüschtier",
    "plüsch",
    "plush",
    "poster",
    "sticker",
    "aufkleber",
    "schlüsselanhänger",
    "keychain",
    "t-shirt",
    "shirt",
    "kostüm",
    "bettwäsche",
    "puzzle",
    "comic",
    "roman",
    "blu-ray",
    "bluray",
    "dvd",
    "soundtrack",
    "sammelkarte",
    "trading card",
    "funko pop",
)
_MAIN_PRODUCT = (
    "evercade",
    "super nintendo",
    "snes",
    "nintendo switch",
    "switch spiel",
    "wii u",
    "game boy",
    "gameboy",
    "playstation",
    "xbox",
    "videospiel",
    "video game",
    "spielmodul",
    "game cartridge",
    "cartridge",
    "pal modul",
    "pal version",
)
_VIDEO_GAME_CATEGORIES = (
    "video games",
    "videospiele",
    "computer games",
    "konsolenspiele",
    "spiele für konsolen",
)
_MERCHANDISE_CATEGORIES = (
    "toys",
    "spielzeug",
    "trading cards",
    "sammelkarten",
    "board games",
    "brettspiele",
    "collectibles",
    "fanartikel",
)


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"\s+", " ", text).strip()


def _signals(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase in text]


def _category_text(listing: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ("category_path", "category_name", "category_id"):
        if listing.get(key):
            values.append(str(listing[key]))
    categories = listing.get("categories")
    if isinstance(categories, list):
        for category in categories:
            if isinstance(category, dict):
                values.extend(
                    str(category.get(key) or "")
                    for key in ("categoryName", "categoryPath", "name", "path")
                )
            elif category:
                values.append(str(category))
    return _normalize(" ".join(values))


def _quantity_bundle_signal(text: str) -> str | None:
    pattern = r"\b(?:[2-9]|[1-9]\d+)\s*(?:x\s*)?(?:spiele|games|module|cartridges?)\b"
    return "mehrere Produkte" if re.search(pattern, text) else None


def _query_target(query: str) -> str:
    text = _normalize(query)
    if _signals(text, _ACCESSORY):
        return "accessory_part"
    if _signals(text, _MERCHANDISE):
        return "related_merchandise"
    if _signals(text, _BUNDLE) or _quantity_bundle_signal(text):
        return "bundle"
    if _signals(text, _WANTED):
        return "wanted"
    if _signals(text, _RENTAL):
        return "rental"
    if _signals(text, _SERVICE):
        return "service"
    return "main_product"


def _title_query_ratio(title: str, query: str) -> float:
    ignored = {"der", "die", "das", "ein", "eine", "und", "oder", "mit", "für", "neu", "ovp"}
    query_tokens = [
        token
        for token in re.findall(r"[a-z0-9äöüß]+", _normalize(query))
        if len(token) > 1 and token not in ignored
    ]
    if not query_tokens:
        return 0.0
    title_tokens = set(re.findall(r"[a-z0-9äöüß]+", title))
    return sum(token in title_tokens for token in query_tokens) / len(query_tokens)


def classify_listing(listing: dict[str, Any], query: str) -> dict[str, Any]:
    """Return an explainable product class and its search relevance."""

    title = _normalize(listing.get("title"))
    category = _category_text(listing)
    target = _query_target(query)

    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("wanted", _WANTED),
        ("rental", _RENTAL),
        ("service", _SERVICE),
        ("bundle", _BUNDLE),
        ("accessory_part", _ACCESSORY),
        ("related_merchandise", _MERCHANDISE),
    )
    code = "unknown"
    signals: list[str] = []
    confidence = "low"
    for candidate, phrases in checks:
        found = _signals(title, phrases)
        if found:
            code, signals, confidence = candidate, found[:4], "high"
            break

    if code == "unknown":
        quantity_signal = _quantity_bundle_signal(title)
        if quantity_signal:
            code, signals, confidence = "bundle", [quantity_signal], "high"
        else:
            category_merch = _signals(category, _MERCHANDISE_CATEGORIES)
            category_game = _signals(category, _VIDEO_GAME_CATEGORIES)
            main = _signals(title, _MAIN_PRODUCT)
            if category_merch:
                code, signals, confidence = "related_merchandise", category_merch[:3], "high"
            elif category_game:
                code, signals, confidence = "main_product", category_game[:3], "high"
            elif main:
                code, signals, confidence = "main_product", main[:4], "medium"
            elif target == "main_product" and _title_query_ratio(title, query) >= 0.75:
                code, signals, confidence = "main_product", ["title-query-match"], "medium"

    if code == target:
        relevance = "accept"
        reason = f"Produktart entspricht der Suche: {CLASS_LABELS[code]}"
    elif code == "unknown":
        relevance = "review"
        reason = "Produktart nicht eindeutig erkannt"
    elif code == "bundle":
        # The established accept_bundles switch remains the single authority.
        relevance = "profile_rule"
        reason = "Mehrere Produkte oder Konvolut erkannt"
    else:
        relevance = "reject"
        reason = f"{CLASS_LABELS[code]} statt gesuchtem {CLASS_LABELS[target]}"

    return {
        "code": code,
        "label": CLASS_LABELS[code],
        "confidence": confidence,
        "relevance": relevance,
        "expected_code": target,
        "expected_label": CLASS_LABELS[target],
        "signals": signals,
        "reason": reason,
        "ruleset": "product-classification-v1",
    }


def apply_classification_metadata(
    listing: dict[str, Any], classification: dict[str, Any]
) -> None:
    """Expose the class in the stable listing/result-info contract."""

    listing["product_classification"] = classification
    info = listing.get("result_info")
    info = dict(info) if isinstance(info, dict) else {}
    info["product_class"] = classification["code"]
    info["product_class_label"] = classification["label"]
    if classification["code"] == "wanted":
        info["offer_type"] = "Gesuch"
    elif classification["code"] == "rental":
        info["offer_type"] = "Vermietung"
    elif classification["code"] == "service":
        info["offer_type"] = "Dienstleistung"
    if classification["code"] == "bundle":
        info["scope"] = "Bundle"
    listing["result_info"] = info


def apply_classification_evaluation(
    evaluation: dict[str, Any], classification: dict[str, Any]
) -> dict[str, Any]:
    """Apply classification as an additive rule without changing the 0.44.4 core."""

    result = dict(evaluation)
    criteria = [dict(item) for item in result.get("criteria") or []]
    relevance = classification.get("relevance")
    if relevance in {"reject", "review"}:
        hard = relevance == "reject"
        color = "red" if hard else "yellow"
        criterion = {
            "name": "Produktart",
            "color": color,
            "reason": classification["reason"],
            "hard": hard,
            "active": True,
        }
        criteria.append(criterion)
        prior_reason = str(result.get("reason") or "").strip()
        if hard:
            result.update(
                color="red",
                label="🔴 Unpassend",
                score=0,
                decision="reject",
                reason=classification["reason"],
            )
        elif result.get("color") == "green":
            result.update(
                color="yellow",
                label="🟡 Prüfen",
                score=min(60, int(result.get("score") or 60)),
                decision="review",
                reason=classification["reason"],
            )
        elif classification["reason"] not in prior_reason:
            result["reason"] = " · ".join(
                part for part in (prior_reason, classification["reason"]) if part
            )[:300]
    result["criteria"] = criteria
    result["active_criteria"] = len(criteria)
    return result


__all__ = [
    "CLASS_LABELS",
    "classify_listing",
    "apply_classification_metadata",
    "apply_classification_evaluation",
]
