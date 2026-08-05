"""SNES-PAL-Profiladapter für GenericParser module v1."""
from __future__ import annotations

from collections.abc import Iterable

from ..module_api import ModuleSearchProfile


def _terms(values: Iterable[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def snes_pal_profile(
    title: str,
    *,
    profile_id: str | None = None,
    variants: Iterable[str] = (),
    max_price: float | None = None,
    market_value: float | None = None,
    excluded_terms: Iterable[str] = ("NTSC", "Repro", "Reproduction"),
    accept_bundles: bool = False,
    accept_incomplete: bool = False,
) -> ModuleSearchProfile:
    """Erzeugt ein Suchprofil für einen europäischen SNES-PAL-Titel."""

    name = title.strip()
    if not name:
        raise ValueError("title darf nicht leer sein")
    return ModuleSearchProfile(
        profile_id=profile_id or f"snes-pal:{name.casefold().replace(' ', '-')}",
        display_name=f"SNES PAL · {name}",
        query=f"SNES {name}",
        required_terms=["PAL"],
        excluded_terms=_terms(excluded_terms),
        model_patterns=_terms(variants),
        brands=["Nintendo"],
        max_price=max_price,
        market_value=market_value,
        accept_bundles=accept_bundles,
        accept_incomplete=accept_incomplete,
    )


__all__ = ["snes_pal_profile"]
