from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .models import SearchProfile


class ConfigurationError(ValueError):
    """Ungültige oder nicht unterstützte Suchprofil-Konfiguration."""


def _as_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ConfigurationError(f"{field_name} muss eine Liste von Textwerten sein")
    result = tuple(str(item).strip() for item in value)
    if any(not item for item in result):
        raise ConfigurationError(f"{field_name} darf keine leeren Einträge enthalten")
    return result


def _as_decimal(value: Any, *, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ConfigurationError(f"{field_name} muss eine Zahl sein") from exc


def _as_postal_code(value: Any) -> str | None:
    if value is None or value == "":
        return None
    postal_code = str(value).strip()
    if len(postal_code) != 5 or not postal_code.isdigit():
        raise ConfigurationError("postal_code muss eine fünfstellige deutsche PLZ sein")
    return postal_code


def _as_bool(value: Any, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "ja", "1"}:
            return True
        if normalized in {"false", "no", "nein", "0"}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ConfigurationError(f"{field_name} muss ein Wahrheitswert sein")


def profile_from_dict(data: Mapping[str, Any]) -> SearchProfile:
    """Erzeugt ein validiertes SearchProfile aus einem Dictionary."""

    if not isinstance(data, Mapping):
        raise ConfigurationError("Ein Suchprofil muss ein Objekt sein")
    try:
        profile = SearchProfile(
            id=str(data["id"]).strip(),
            display_name=str(data["display_name"]).strip(),
            search_queries=_as_tuple(data.get("search_queries"), field_name="search_queries"),
            category_paths=_as_tuple(data.get("category_paths"), field_name="category_paths"),
            brands=_as_tuple(data.get("brands"), field_name="brands"),
            product_types=_as_tuple(data.get("product_types"), field_name="product_types"),
            model_patterns=_as_tuple(data.get("model_patterns"), field_name="model_patterns"),
            required_any=_as_tuple(data.get("required_any"), field_name="required_any"),
            excluded_terms=_as_tuple(data.get("excluded_terms"), field_name="excluded_terms"),
            max_price=_as_decimal(data.get("max_price"), field_name="max_price"),
            market_value=_as_decimal(data.get("market_value"), field_name="market_value"),
            postal_code=_as_postal_code(data.get("postal_code")),
            location_id=(int(data["location_id"]) if data.get("location_id") is not None else None),
            radius_km=(int(data["radius_km"]) if data.get("radius_km") is not None else None),
            shipping_allowed=_as_bool(
                data.get("shipping_allowed"), field_name="shipping_allowed", default=True
            ),
            accept_bundles=_as_bool(
                data.get("accept_bundles"), field_name="accept_bundles", default=False
            ),
            accept_incomplete=_as_bool(
                data.get("accept_incomplete"), field_name="accept_incomplete", default=False
            ),
        )
    except KeyError as exc:
        raise ConfigurationError(f"Pflichtfeld fehlt: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError(str(exc)) from exc
    return profile


def profile_to_dict(profile: SearchProfile) -> dict[str, Any]:
    """Serialisiert ein SearchProfile ohne Verlust fachlicher Werte."""

    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "search_queries": list(profile.search_queries),
        "category_paths": list(profile.category_paths),
        "brands": list(profile.brands),
        "product_types": list(profile.product_types),
        "model_patterns": list(profile.model_patterns),
        "required_any": list(profile.required_any),
        "excluded_terms": list(profile.excluded_terms),
        "max_price": str(profile.max_price) if profile.max_price is not None else None,
        "market_value": str(profile.market_value) if profile.market_value is not None else None,
        "postal_code": profile.postal_code,
        "location_id": profile.location_id,
        "radius_km": profile.radius_km,
        "shipping_allowed": profile.shipping_allowed,
        "accept_bundles": profile.accept_bundles,
        "accept_incomplete": profile.accept_incomplete,
    }


def load_profiles(path: str | Path) -> tuple[SearchProfile, ...]:
    """Lädt ein oder mehrere Suchprofile aus JSON oder YAML."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Konfiguration kann nicht gelesen werden: {source}") from exc

    suffix = source.suffix.casefold()
    try:
        if suffix == ".json":
            raw = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(text)
        else:
            raise ConfigurationError("Unterstützt werden nur .json, .yaml und .yml")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Ungültige Konfigurationsdatei: {source}") from exc

    items = raw.get("profiles") if isinstance(raw, Mapping) and "profiles" in raw else raw
    if isinstance(items, Mapping):
        items = [items]
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise ConfigurationError("Die Datei muss ein Profil oder eine Liste von Profilen enthalten")
    profiles = tuple(profile_from_dict(item) for item in items)
    if not profiles:
        raise ConfigurationError("Mindestens ein Suchprofil ist erforderlich")
    ids = [profile.id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ConfigurationError("Profil-IDs müssen innerhalb einer Datei eindeutig sein")
    return profiles


def load_profile(path: str | Path) -> SearchProfile:
    profiles = load_profiles(path)
    if len(profiles) != 1:
        raise ConfigurationError("Die Datei enthält mehrere Profile; load_profiles verwenden")
    return profiles[0]


def save_profiles(path: str | Path, profiles: Sequence[SearchProfile]) -> None:
    """Speichert Suchprofile deterministisch als JSON oder YAML."""

    destination = Path(path)
    if not profiles:
        raise ConfigurationError("Mindestens ein Suchprofil ist erforderlich")
    payload = {"profiles": [profile_to_dict(profile) for profile in profiles]}
    suffix = destination.suffix.casefold()
    if suffix == ".json":
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    elif suffix in {".yaml", ".yml"}:
        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    else:
        raise ConfigurationError("Unterstützt werden nur .json, .yaml und .yml")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def save_profile(path: str | Path, profile: SearchProfile) -> None:
    save_profiles(path, (profile,))
