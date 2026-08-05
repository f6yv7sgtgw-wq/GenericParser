"""Evercade-Profiladapter für GenericParser module v1."""
from __future__ import annotations

from collections.abc import Iterable

from ..module_api import ModuleSearchProfile


def _terms(values: Iterable[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def evercade_profile(
    cartridge_name: str,
    *,
    profile_id: str | None = None,
    variants: Iterable[str] = (),
    max_price: float | None = None,
    market_value: float | None = None,
    excluded_terms: Iterable[str] = (),
    accept_bundles: bool = False,
    accept_incomplete: bool = False,
) -> ModuleSearchProfile:
    """Erzeugt ein neutrales Suchprofil für eine Evercade-Cartridge.

    Projektspezifische Sammlungs- oder Kaufentscheidungen bleiben außerhalb
    des Parsermoduls. Der Adapter übersetzt nur Namen, Varianten und Preise.
    """

    name = cartridge_name.strip()
    if not name:
        raise ValueError("cartridge_name darf nicht leer sein")
    return ModuleSearchProfile(
        profile_id=profile_id or f"evercade:{name.casefold().replace(' ', '-')}",
        display_name=f"Evercade · {name}",
        query=f"Evercade {name}",
        model_patterns=_terms(variants),
        brands=["Evercade", "Blaze"],
        excluded_terms=_terms(excluded_terms),
        max_price=max_price,
        market_value=market_value,
        accept_bundles=accept_bundles,
        accept_incomplete=accept_incomplete,
    )


__all__ = ["evercade_profile"]
