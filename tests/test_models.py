from decimal import Decimal

import pytest

from generic_parser import SearchProfile


def test_search_profile_validates_required_values() -> None:
    with pytest.raises(ValueError, match="search_query"):
        SearchProfile(id="x", display_name="X", search_queries=())


def test_search_profile_accepts_decimal_limits() -> None:
    profile = SearchProfile(
        id="x",
        display_name="X",
        search_queries=("x",),
        max_price=Decimal("12.50"),
    )
    assert profile.max_price == Decimal("12.50")
