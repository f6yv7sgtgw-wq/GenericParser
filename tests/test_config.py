from pathlib import Path
from decimal import Decimal

import pytest

from generic_parser import (
    ConfigurationError,
    SearchProfile,
    load_profile,
    load_profiles,
    profile_from_dict,
    profile_to_dict,
    save_profile,
    save_profiles,
)


def sample_profile() -> SearchProfile:
    return SearchProfile(
        id="evercade-test",
        display_name="Evercade Test",
        search_queries=("evercade test",),
        brands=("evercade",),
        max_price=Decimal("35.00"),
        postal_code="37136",
        radius_km=50,
    )


def test_profile_dict_roundtrip() -> None:
    profile = sample_profile()
    assert profile_from_dict(profile_to_dict(profile)) == profile


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".yml"])
def test_file_roundtrip(tmp_path, suffix: str) -> None:
    path = tmp_path / f"profile{suffix}"
    profile = sample_profile()
    save_profile(path, profile)
    assert load_profile(path) == profile


def test_multiple_profiles_and_unique_ids(tmp_path) -> None:
    path = tmp_path / "profiles.yaml"
    first = sample_profile()
    second = SearchProfile(id="snes-test", display_name="SNES Test", search_queries=("snes test",))
    save_profiles(path, (first, second))
    assert load_profiles(path) == (first, second)


def test_duplicate_profile_ids_are_rejected(tmp_path) -> None:
    path = tmp_path / "profiles.json"
    profile = sample_profile()
    save_profiles(path, (profile, profile))
    with pytest.raises(ConfigurationError, match="eindeutig"):
        load_profiles(path)


def test_missing_required_field_is_clear_error() -> None:
    with pytest.raises(ConfigurationError, match="display_name"):
        profile_from_dict({"id": "x", "search_queries": ["x"]})


def test_string_boolean_values_are_parsed_explicitly() -> None:
    profile = profile_from_dict(
        {
            "id": "x",
            "display_name": "X",
            "search_queries": ["x"],
            "shipping_allowed": "false",
            "accept_bundles": "ja",
        }
    )
    assert profile.shipping_allowed is False
    assert profile.accept_bundles is True


def test_invalid_boolean_value_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="Wahrheitswert"):
        profile_from_dict(
            {
                "id": "x",
                "display_name": "X",
                "search_queries": ["x"],
                "shipping_allowed": "vielleicht",
            }
        )


def test_repository_example_profiles_load() -> None:
    root = Path(__file__).resolve().parents[1]
    assert load_profile(root / "examples/evercade_sunsoft_collection_1.yaml").id.startswith("evercade-")
    assert load_profile(root / "examples/snes_zelda_link_to_the_past.json").id.startswith("snes-")


def test_invalid_postal_code_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="fünfstellige"):
        profile_from_dict(
            {
                "id": "x",
                "display_name": "X",
                "search_queries": ["x"],
                "postal_code": "123",
            }
        )


def test_profile_roundtrip_preserves_kleinanzeigen_location_and_categories(tmp_path: Path) -> None:
    profile = profile_from_dict(
        {
            "id": "category-local",
            "display_name": "Lokale Videospiele",
            "category_paths": ["s-videospiele"],
            "postal_code": "37075",
            "location_id": 1234,
            "radius_km": 25,
        }
    )
    target = tmp_path / "local.yaml"
    save_profile(target, profile)
    loaded = load_profile(target)
    assert loaded.category_paths == ("s-videospiele",)
    assert loaded.location_id == 1234
    assert loaded.radius_km == 25
