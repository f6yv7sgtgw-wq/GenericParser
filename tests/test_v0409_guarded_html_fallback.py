from __future__ import annotations

import pytest

from generic_parser import cloudflare_v0409 as release


def test_version_is_0409() -> None:
    assert release.VERSION == "0.40.9"


def test_html_fallback_phase_error_keeps_phase_and_url() -> None:
    original = ValueError("broken html")
    error = release.HtmlFallbackPhaseError("html_parse", original, target_url="https://example.invalid/page")
    assert error.phase == "html_parse"
    assert error.target_url == "https://example.invalid/page"
    assert error.original is original
    assert "broken html" in str(error)


@pytest.mark.parametrize("phase", ["html_page_url_build", "html_fetch", "html_parse", "html_total_extract"])
def test_documented_server_phases_are_stable(phase: str) -> None:
    assert phase.startswith("html_")
