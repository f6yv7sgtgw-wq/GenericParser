"""Zeitraum-Kriterium: Wie alt darf eine Anzeige sein?

Die Marktplätze führen teils jahrealte Festpreisangebote (im Lemmings-Lauf
standen eBay-Anzeigen von 2017). Der Zeitraum ist ein reguläres Suchkriterium
im selben Muster wie ``max_price``: additiv am Ampelergebnis, keine stille
Kürzung — zu alte Treffer werden Rot und bleiben über den Statusfilter
sichtbar. Anzeigen **ohne** Einstelldatum werden bewusst durchgelassen
(betrifft vor allem Vinted): Ein Filter, der nichts prüfen kann, darf nichts
aussortieren.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

CRITERION_NAME = "Zeitraum"


def _parse_posted_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def evaluate_listing_age(
    posted_at: Any,
    max_age_days: Any,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Prüft das Einstelldatum gegen den Zeitraum; None heißt: nichts zu tun.

    None kommt zurück, wenn kein Zeitraum gesetzt ist oder die Anzeige kein
    lesbares Datum trägt — in beiden Fällen bleibt die Bewertung unberührt.
    """

    try:
        limit_days = int(max_age_days) if max_age_days is not None else None
    except (TypeError, ValueError):
        return None
    if not limit_days or limit_days <= 0:
        return None
    posted = _parse_posted_at(posted_at)
    if posted is None:
        return None
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    age_days = (reference - posted) / timedelta(days=1)
    if age_days <= limit_days:
        return None
    return {
        "max_age_days": limit_days,
        "age_days": int(age_days),
        "posted_at": posted.isoformat(),
        "reason": f"Anzeige ist {int(age_days)} Tage alt (Zeitraum: {limit_days} Tage)",
    }


def apply_age_evaluation(
    evaluation: dict[str, Any], violation: dict[str, Any] | None
) -> dict[str, Any]:
    """Wendet einen Zeitraum-Verstoß als hartes Rot an — analog zu max_price."""

    if not violation:
        return evaluation
    result = dict(evaluation)
    criteria = [dict(item) for item in result.get("criteria") or []]
    criteria.append(
        {
            "name": CRITERION_NAME,
            "color": "red",
            "reason": violation["reason"],
            "hard": True,
            "active": True,
        }
    )
    result.update(
        color="red",
        label="🔴 Unpassend",
        score=0,
        decision="reject",
        reason=violation["reason"],
        criteria=criteria,
        active_criteria=len(criteria),
    )
    return result


__all__ = ["CRITERION_NAME", "evaluate_listing_age", "apply_age_evaluation"]
