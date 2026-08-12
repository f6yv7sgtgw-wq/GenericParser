"""Quellenneutrale Relevanzprüfung: Passt ein Treffer zur Suchanfrage?

Die Marktplatzsuchen arbeiten mit ODER-Semantik über die Anfragewörter, deshalb
liefert „super mario kart 8" auch jedes andere Mario-Spiel. Der
Produktklassifizierer beantwortet nur die Produktart, nicht die Passung zur
Anfrage. Dieses Modul misst deshalb die Deckung der tragenden Anfragebegriffe
im Titel (schwächer in der Beschreibung) und gibt das Ergebnis additiv aus —
analog zu ``classification``. Es filtert nie hart: Die Zusage „keine stille
Kürzung" gilt, unpassende Treffer werden nur Rot markiert.
"""
from __future__ import annotations

from typing import Any

from .normalization import normalize_text

RULESET = "relevance-v1"

# Füllwörter dürfen allein keinen Treffer rechtfertigen. Die Liste ist bewusst
# klein und in normalisierter Schreibweise gehalten (normalize_text macht aus
# „für" ein „fuer").
_STOPWORDS = frozenset(
    {
        # Artikel, Konjunktionen, Präpositionen
        "der", "die", "das", "den", "dem", "ein", "eine", "einen", "einem",
        "und", "oder", "mit", "ohne", "fuer", "von", "aus", "auf", "in", "im",
        "the", "and", "for", "of", "with",
        # Marktplatz-Füllwörter
        "super", "neu", "neue", "neuer", "neues", "original", "originale",
        "ovp", "set", "top", "mega", "inkl", "inklusive",
    }
)

# Zahlen wiegen doppelt: „Mario Kart 8" ohne die 8 ist ein anderes Produkt,
# während ein fehlendes Beiwort nur die Deckung senkt.
_NUMBER_WEIGHT = 2.0
_WORD_WEIGHT = 1.0
# Die Beschreibung zählt schwächer, weil sie bei Konvoluten alles Mögliche nennt.
_DESCRIPTION_WEIGHT = 0.5

_MATCH_THRESHOLD = 0.75
_MISMATCH_THRESHOLD = 0.4


def _tokens(value: object) -> list[str]:
    return normalize_text(str(value or "")).split()


def _carrying_terms(query: str) -> list[str]:
    """Zerlegt die Anfrage in tragende Begriffe (Substantive/Namen und Zahlen).

    Besteht die Anfrage nur aus Füllwörtern, tragen ersatzweise alle Wörter —
    sonst wäre gar keine Prüfung möglich.
    """

    tokens = _tokens(query)
    carrying = [t for t in tokens if t not in _STOPWORDS and (len(t) > 1 or t.isdigit())]
    if not carrying:
        carrying = [t for t in tokens if len(t) > 1 or t.isdigit()]
    seen: set[str] = set()
    ordered: list[str] = []
    for term in carrying:
        if term not in seen:
            seen.add(term)
            ordered.append(term)
    return ordered


def _abbreviations(words: list[str], numbers: list[str]) -> dict[str, tuple[str, ...]]:
    """Abkürzungen wie „MK8" für „mario kart 8".

    Initialen aufeinanderfolgender tragender Wörter plus Zahl. Ohne Zahl erst
    ab drei Initialen — „MK" allein wäre zu unspezifisch.
    """

    abbreviations: dict[str, tuple[str, ...]] = {}
    for start in range(len(words)):
        for end in range(start + 2, len(words) + 1):
            initials = "".join(word[0] for word in words[start:end])
            covered = tuple(words[start:end])
            if end - start >= 3:
                abbreviations[initials] = covered
            for number in numbers:
                abbreviations[initials + number] = covered + (number,)
    return abbreviations


def _match_in_tokens(
    words: list[str],
    numbers: list[str],
    tokens: list[str],
    abbreviations: dict[str, tuple[str, ...]],
) -> set[str]:
    token_set = set(tokens)
    matched: set[str] = set()
    # Titel-Tokens, die Begriffe gedeckt haben — Bezugspunkt für die
    # Nachbarschaftsprüfung der Zahlen.
    matching_tokens: set[str] = set()

    for word in words:
        if word in token_set:
            matched.add(word)
            matching_tokens.add(word)

    # Zusammenschreibungen: „MarioKart" deckt beide Wörter.
    for first, second in zip(words, words[1:]):
        compound = first + second
        if compound in token_set:
            matched.update((first, second))
            matching_tokens.add(compound)

    # Abkürzungen decken alle enthaltenen Begriffe auf einmal.
    for token in token_set:
        covered = abbreviations.get(token)
        if covered:
            matched.update(covered)
            matching_tokens.add(token)

    # Zahlen sind heikel: „8" zählt nur neben einem deckenden Token
    # („Mario Kart 8"), nicht frei stehend („Set von 8") und nicht gar nicht
    # („Mario Kart" ohne Zahl).
    for number in numbers:
        if number in matched:
            continue
        for index, token in enumerate(tokens):
            if token != number:
                continue
            neighbours = tokens[max(index - 1, 0):index] + tokens[index + 1:index + 2]
            if any(neighbour in matching_tokens for neighbour in neighbours):
                matched.add(number)
                break
        if number not in matched:
            # Angeschriebene Form wie „Kart8" deckt Wort und Zahl zugleich.
            for word in words:
                if word + number in token_set or number + word in token_set:
                    matched.update((word, number))
                    break

    return matched


def evaluate_relevance(
    query: str,
    title: object,
    description: object = None,
) -> dict[str, Any]:
    """Misst die Deckung der Anfrage im Treffer; additives Ergebnis 0..1."""

    terms = _carrying_terms(str(query or ""))
    if not terms:
        return {
            "score": 1.0,
            "verdict": "match",
            "terms": [],
            "matched_terms": [],
            "missing_terms": [],
            "reason": "Keine prüfbaren Suchbegriffe",
            "ruleset": RULESET,
        }

    words = [term for term in terms if not term.isdigit()]
    numbers = [term for term in terms if term.isdigit()]
    abbreviations = _abbreviations(words, numbers)

    title_matched = _match_in_tokens(words, numbers, _tokens(title), abbreviations)
    description_matched = _match_in_tokens(
        words, numbers, _tokens(description), abbreviations
    )

    total = 0.0
    credit = 0.0
    matched_terms: list[str] = []
    missing_terms: list[str] = []
    for term in terms:
        weight = _NUMBER_WEIGHT if term.isdigit() else _WORD_WEIGHT
        total += weight
        if term in title_matched:
            credit += weight
            matched_terms.append(term)
        elif term in description_matched:
            credit += weight * _DESCRIPTION_WEIGHT
            matched_terms.append(term)
        else:
            missing_terms.append(term)

    score = credit / total
    if score >= _MATCH_THRESHOLD:
        verdict = "match"
        reason = "Suchbegriffe im Titel gedeckt"
    elif score >= _MISMATCH_THRESHOLD:
        verdict = "review"
        reason = f"Suchbegriffe nur teilweise gedeckt (fehlt: {', '.join(missing_terms)})"
    else:
        verdict = "mismatch"
        if missing_terms:
            reason = f"Suchbegriffe fehlen im Titel: {', '.join(missing_terms)}"
        else:
            reason = "Suchbegriffe im Titel nicht gedeckt"

    return {
        "score": round(score, 3),
        "verdict": verdict,
        "terms": terms,
        "matched_terms": matched_terms,
        "missing_terms": missing_terms,
        "reason": reason,
        "ruleset": RULESET,
    }


def apply_relevance_metadata(listing: dict[str, Any], relevance: dict[str, Any]) -> None:
    """Legt das Ergebnis additiv am Listing ab — analog zu classification."""

    listing["relevance"] = relevance


def apply_relevance_evaluation(
    evaluation: dict[str, Any], relevance: dict[str, Any]
) -> dict[str, Any]:
    """Wendet die Relevanz als additive Ampelregel an, ohne hart zu filtern.

    Unter der Schwelle wird der Treffer Rot, im Graubereich Gelb (Prüffall).
    Rote Treffer bleiben abrufbar — der Nutzer sieht sie über den Statusfilter.
    """

    result = dict(evaluation)
    criteria = [dict(item) for item in result.get("criteria") or []]
    verdict = relevance.get("verdict")
    if verdict in {"mismatch", "review"}:
        hard = verdict == "mismatch"
        color = "red" if hard else "yellow"
        criteria.append(
            {
                "name": "Relevanz",
                "color": color,
                "reason": relevance["reason"],
                "hard": hard,
                "active": True,
            }
        )
        prior_reason = str(result.get("reason") or "").strip()
        if hard:
            result.update(
                color="red",
                label="🔴 Unpassend",
                score=0,
                decision="reject",
                reason=relevance["reason"],
            )
        elif result.get("color") == "green":
            result.update(
                color="yellow",
                label="🟡 Prüfen",
                score=min(60, int(result.get("score") or 60)),
                decision="review",
                reason=relevance["reason"],
            )
        elif relevance["reason"] not in prior_reason:
            result["reason"] = " · ".join(
                part for part in (prior_reason, relevance["reason"]) if part
            )[:300]
    result["criteria"] = criteria
    result["active_criteria"] = len(criteria)
    return result


__all__ = [
    "RULESET",
    "evaluate_relevance",
    "apply_relevance_metadata",
    "apply_relevance_evaluation",
]
