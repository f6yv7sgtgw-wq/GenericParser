from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNTIME_DIR = ROOT / "src/generic_parser"
ENTRY_PATH = RUNTIME_DIR / "worker_runtime_v04452_entry.py"
WORKER_PATH = RUNTIME_DIR / "cloudflare_worker.py"
CONTROLLER_PATH = ROOT / "cloudflare/public/controller-04452.js"


def _load_runtime():
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        spec = importlib.util.spec_from_file_location("worker_runtime_v04452_entry_test", ENTRY_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


runtime = _load_runtime()


def _page_html(count=25, start_id=3500000000, next_href="/s-seite:2/snes/k0"):
    cards = []
    for index in range(count):
        listing_id = start_id + index
        cards.append(f"""
        <li class="ad-listitem lazyload-item">
          <a href="/s-anzeige/snes-spiel-{index}/{listing_id}-227-1000">
            <h2>SNES Spiel {index}</h2>
          </a>
          <div class="aditem-main--top--left">37136 Waake</div>
          <div class="aditem-main--middle--price-shipping--price">{10 + index} €</div>
        </li>
        """)
    navigation = f"""
      <div class="navigation"><a href="/s-anzeige/navigation/{start_id + 999}-227-1000">Navigation</a></div>
    """
    next_link = f'<a class="pagination-next" href="{next_href}">Weiter</a>' if next_href else ""
    return f'<div>{count} Ergebnisse</div>{navigation}{"".join(cards)}{next_link}'


def test_direct_worker_stays_framework_free_and_uses_safe_entry():
    source = WORKER_PATH.read_text(encoding="utf-8")
    assert "import worker_runtime_v04452_entry as runtime" in source
    for marker in (
        "import importlib",
        "from fastapi",
        "import fastapi",
        "from pydantic",
        "import pydantic",
        "import asgi",
        "import httpx",
        "from generic_parser",
    ):
        assert marker not in source


def test_complete_card_windows_remove_navigation_and_recover_prices():
    html = _page_html()

    async def fake_fetch(_url):
        return html

    payload = runtime.SearchPayload({"query": "Snes", "page": 0})
    result = asyncio.run(runtime.search_page(payload, fake_fetch))

    assert result["summary"]["fetched_listings"] == 7
    assert all(item["price"] is not None for item in result["listings"])
    assert all(item["title"] != "Navigation" for item in result["listings"])
    diagnostics = result["coverage_diagnostics"]
    assert diagnostics["navigation_candidates_removed"] == 1
    assert diagnostics["price_recognized_count"] == 7
    assert diagnostics["price_missing_count"] == 0
    assert diagnostics["extraction_strategy"] == "s_anzeige_complete_container_windows"


def test_finished_source_page_jumps_to_next_packet_boundary_and_cursor():
    html = _page_html(count=25, next_href="/s-seite:2/snes/k0")

    async def fake_fetch(_url):
        return html

    payload = runtime.SearchPayload({"query": "Snes", "page": 3})
    result = asyncio.run(runtime.search_page(payload, fake_fetch))
    pagination = result["pagination"]

    assert result["summary"]["fetched_listings"] == 4
    assert pagination["cursor_transition"] is True
    assert pagination["next_page"] == 4
    assert pagination["cursor_url"].endswith("/s-seite:2/snes/k0")
    assert result["coverage_diagnostics"]["cursor_next_page"] == 4


def test_cursor_url_is_used_for_next_physical_source_page():
    requested = []
    html = _page_html(count=25, start_id=3600000000, next_href="/s-seite:3/snes/k0")

    async def fake_fetch(url):
        requested.append(url)
        return html

    cursor = "https://www.kleinanzeigen.de/s-seite:2/snes/k0"
    payload = runtime.SearchPayload({"query": "Snes", "page": 4, "cursor_url": cursor})
    result = asyncio.run(runtime.search_page(payload, fake_fetch))

    assert requested == [cursor]
    assert result["pagination"]["actual_source_url"] == cursor
    assert result["coverage_diagnostics"]["actual_source_url"] == cursor


def test_controller_persists_cursor_and_emits_coverage_events():
    source = CONTROLLER_PATH.read_text(encoding="utf-8")
    assert "cursor_url" in source
    assert "cursor_saved" in source
    assert "cursor_applied" in source
    assert "coverage_diagnostics" in source
    assert "priceRecognized" in source


def test_identity_marks_04452_runtime():
    identity = runtime.identity()
    assert identity["version"] == "0.44.5.2"
    assert identity["runtime_model"] == "direct-worker-stdlib-cursor-price-v1"
    assert identity["safe_extractor_binding"] is True
