from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from enum import Enum
from typing import Iterable, Sequence

from .models import Listing, MatchDecision, MatchResult, SearchProfile


class ListingClass(str, Enum):
    PRODUCT = "produkt"
    BUNDLE = "konvolut"
    ACCESSORY = "zubehoer"
    WANTED = "gesuch"
    JOB = "stellenanzeige"
    DEFECT = "defekt"


DEFAULT_ACCESSORY_TERMS = (
    "controller", "kabel", "netzteil", "adapter", "halter", "hülle", "huelle",
    "case", "tasche", "cover", "display", "ständer", "staender", "ersatzteil",
)
DEFAULT_WANTED_TERMS = ("suche", "gesucht", "ankauf", "kaufe", "wanted")
DEFAULT_JOB_TERMS = ("job", "stelle", "stellenangebot", "mitarbeiter", "m/w/d", "vollzeit", "teilzeit")
DEFAULT_DEFECT_TERMS = ("defekt", "kaputt", "bastler", "reparatur", "ohne funktion", "ungetestet")
DEFAULT_BUNDLE_TERMS = ("sammlung", "konvolut", "paket", "bundle", "mehrere", "spiele lot", "set")
NEGATIONS = ("nicht", "kein", "keine", "ohne")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def variants(term: str) -> set[str]:
    base = normalize(term)
    values = {base, base.replace(" ", ""), base.replace(" ", "-")}
    tokens = base.split()
    roman = {"1": "i", "2": "ii", "3": "iii", "4": "iv"}
    for index, token in enumerate(tokens):
        if token in roman:
            alt = tokens.copy()
            alt[index] = roman[token]
            values.add(" ".join(alt))
            values.add("".join(alt))
    return {value for value in values if value}


def contains(text: str, term: str) -> bool:
    compact = text.replace(" ", "")
    return any(v in text or v.replace("-", "") in compact for v in variants(term))


def _negated(text: str, term: str) -> bool:
    words = text.split()
    target = normalize(term).split()
    if not target:
        return False
    first = target[0]
    for idx, word in enumerate(words):
        if word == first and any(n in words[max(0, idx - 3):idx] for n in NEGATIONS):
            return True
    return False


def _has_any(text: str, terms: Iterable[str], *, ignore_negated: bool = False) -> list[str]:
    found = []
    for term in terms:
        if contains(text, term) and not (ignore_negated and _negated(text, term)):
            found.append(term)
    return found


def classify_listing(listing: Listing) -> tuple[ListingClass, tuple[str, ...]]:
    text = normalize(f"{listing.title} {listing.description or ''}")
    wanted = _has_any(text, DEFAULT_WANTED_TERMS)
    if wanted:
        return ListingClass.WANTED, tuple(wanted)
    jobs = _has_any(text, DEFAULT_JOB_TERMS)
    if jobs:
        return ListingClass.JOB, tuple(jobs)
    defect = _has_any(text, DEFAULT_DEFECT_TERMS, ignore_negated=True)
    if defect:
        return ListingClass.DEFECT, tuple(defect)
    bundle = _has_any(text, DEFAULT_BUNDLE_TERMS)
    if bundle:
        return ListingClass.BUNDLE, tuple(bundle)
    accessory = _has_any(text, DEFAULT_ACCESSORY_TERMS)
    if accessory:
        return ListingClass.ACCESSORY, tuple(accessory)
    return ListingClass.PRODUCT, ()


def score_listing(listing: Listing, profile: SearchProfile) -> MatchResult:
    text = normalize(f"{listing.title} {listing.description or ''}")
    title = normalize(listing.title)
    positive: list[str] = []
    warnings: list[str] = []
    score = 0

    product_class, _ = classify_listing(listing)
    if product_class in {ListingClass.WANTED, ListingClass.JOB}:
        return MatchResult(listing, profile, 0, MatchDecision.REJECT, warnings=(f"Trefferklasse: {product_class.value}",), reason="Nicht verkaufsrelevante Anzeige")
    if product_class is ListingClass.ACCESSORY:
        warnings.append("Zubehör erkannt")
        score -= 45
    elif product_class is ListingClass.DEFECT:
        warnings.append("Defekt/Bastler erkannt")
        score -= 55
    elif product_class is ListingClass.BUNDLE:
        positive.append("Konvolut erkannt")
        score += 8 if profile.accept_bundles else -25

    excluded = _has_any(text, profile.excluded_terms, ignore_negated=True)
    if excluded:
        return MatchResult(listing, profile, 0, MatchDecision.REJECT, warnings=tuple(f"Ausschlussbegriff: {x}" for x in excluded), reason="Ausschlussbegriff gefunden")

    required = tuple(profile.required_any or profile.model_patterns or profile.search_queries)
    matched_required = [term for term in required if contains(text, term)]
    if required and not matched_required:
        return MatchResult(listing, profile, max(0, score), MatchDecision.REJECT, warnings=("Kein Pflichtbegriff gefunden",), reason="Pflichtbegriffe fehlen")
    for term in matched_required:
        score += 40 if contains(title, term) else 20
        positive.append(f"Begriff: {term}")

    for term in profile.brands:
        if contains(text, term):
            score += 12
            positive.append(f"Marke: {term}")
    for term in profile.product_types:
        if contains(text, term):
            score += 8
            positive.append(f"Produkttyp: {term}")

    if listing.price.amount is not None:
        if profile.max_price is not None:
            if listing.price.amount <= profile.max_price:
                score += 15
                positive.append("Preis innerhalb Limit")
            else:
                warnings.append("Preis über Limit")
                score -= 35
        if profile.market_value and profile.market_value > 0:
            ratio = listing.price.amount / profile.market_value
            if ratio <= Decimal("0.75"):
                score += 12
                positive.append("Deutlich unter Richtwert")
            elif ratio >= Decimal("1.25"):
                score -= 10
                warnings.append("Über Richtwert")

    if product_class is ListingClass.DEFECT and not profile.accept_incomplete:
        decision = MatchDecision.REJECT
    elif product_class is ListingClass.ACCESSORY:
        decision = MatchDecision.REJECT
    elif score >= 55:
        decision = MatchDecision.ALERT
    elif score >= 25:
        decision = MatchDecision.REVIEW
    else:
        decision = MatchDecision.REJECT

    reason = "; ".join(positive[:3] or warnings[:3] or ("Keine starken Signale",))
    return MatchResult(listing, profile, max(0, min(score, 100)), decision, tuple(positive), tuple(warnings), reason, should_alert=decision is MatchDecision.ALERT)


def sort_results(results: Sequence[MatchResult], order: str) -> list[MatchResult]:
    if order == "price_asc":
        return sorted(results, key=lambda r: (r.listing.price.amount is None, r.listing.price.amount or Decimal("999999"), -r.score))
    if order == "price_desc":
        return sorted(results, key=lambda r: (r.listing.price.amount is None, -(r.listing.price.amount or Decimal(0)), -r.score))
    if order == "date":
        return sorted(results, key=lambda r: r.listing.posted_at or r.listing.first_seen, reverse=True)
    return sorted(results, key=lambda r: (r.score, r.listing.posted_at or r.listing.first_seen), reverse=True)
