import json
import math
import re
from pathlib import Path

from generic_parser.release_identity import BUILD_ID, VERSION


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_134_layout_contract_remains_active_in_current_release() -> None:
    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert metadata["version"] == VERSION
    assert metadata["build_id"] == BUILD_ID
    assert metadata["verification"]["dense_result_card_grid"] == "required"
    assert metadata["verification"]["side_by_side_card_media"] == "required"
    assert metadata["rollback_plan"] == {
        "last_stable_baseline": "1.6.1",
        "build_id": "gp-161-20260810-1",
    }
    assert public["version"] == VERSION
    assert public["build_id"] == BUILD_ID


def test_search_header_removes_only_the_decorative_project_mark() -> None:
    html = read("cloudflare/public/index.html")
    header = html[: html.index("</header>")]
    assert 'class="brand-mark"' not in header
    assert "GenericParser" in header
    assert 'class="version-badge"' in header
    assert "Log &amp; Diagnose" in header
    assert 'id="connection"' in header


def test_dense_grid_keeps_cards_below_one_third_on_desktop() -> None:
    css = read("cloudflare/public/ui-134.css")
    width = re.search(r"width: min\((\d+)px, calc\(100vw - (\d+)px\)\);", css)
    grid = re.search(
        r"grid-template-columns: repeat\(auto-fit, minmax\(min\((\d+)px, 100%\), 1fr\)\);",
        css,
    )
    gap = re.search(r"\.results \{[\s\S]*?gap: (\d+)px;", css)
    assert width and grid and gap
    max_width, inset = map(int, width.groups())
    min_card = int(grid.group(1))
    card_gap = int(gap.group(1))

    for viewport in (900, 1024, 1200, 1440, 1600):
        content = min(max_width, viewport - inset)
        columns = math.floor((content + card_gap) / (min_card + card_gap))
        card_width = (content - card_gap * (columns - 1)) / columns
        assert columns >= 3
        assert card_width <= viewport / 3


def test_thumbnail_and_text_remain_side_by_side_at_every_breakpoint() -> None:
    css = read("cloudflare/public/ui-134.css")
    assert "grid-template-columns: 82px minmax(0, 1fr);" in css
    mobile = css[css.index("@media (max-width: 520px)") :]
    assert "grid-template-columns: 76px minmax(0, 1fr);" in mobile
    assert ".listing {\n    grid-template-columns: 1fr;" not in mobile
    assert "max-height: none;" in mobile


def test_current_ui_asset_and_cache_are_versioned() -> None:
    html = read("cloudflare/public/index.html")
    service_worker = read("cloudflare/public/service-worker.js")
    app = read("cloudflare/public/app.js")
    assert html.index("ui-133.css") < html.index("ui-134.css")
    assert '"./ui-134.css"' in service_worker
    assert "generic-parser-mobile-gp-162" in service_worker
    assert "service-worker.js?v=gp-162" in app


def test_compact_layout_keeps_vinted_description_behavior() -> None:
    base_css = read("cloudflare/public/ui-133.css")
    app = read("cloudflare/public/app.js")
    assert "-webkit-line-clamp: 4" in base_css
    assert ".description-shell.is-expanded .description" in base_css
    assert "Mehr anzeigen" in app
    assert "Weniger anzeigen" in app
    assert "expandedDescriptions" in app
