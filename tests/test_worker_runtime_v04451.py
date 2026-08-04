from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
RUNTIME_DIR = ROOT / "src/generic_parser"
RUNTIME_PATH = RUNTIME_DIR / "worker_runtime_v04451.py"
ENTRY_PATH = RUNTIME_DIR / "cloudflare_worker.py"


def _load_runtime():
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        spec = importlib.util.spec_from_file_location("worker_runtime_v04451_test", RUNTIME_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


runtime = _load_runtime()


def test_direct_worker_uses_hotfix_runtime_without_heavy_frameworks():
    source = ENTRY_PATH.read_text(encoding="utf-8")
    assert "import worker_runtime_v04451 as runtime" in source
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


def test_listing_id_is_recovered_from_s_anzeige_url():
    href = "/s-anzeige/super-mario-world-snes/3475838898-227-1234"
    assert runtime._listing_id_from_href(href) == "3475838898"


def test_link_fallback_extracts_cards_without_article_data_adid():
    html = """
    <div>2 Ergebnisse</div>
    <ul>
      <li class="ad-listitem">
        <a href="/s-anzeige/super-mario-world-snes/3475838898-227-1234">
          <h2>Super Mario World SNES Modul</h2>
        </a>
        <div class="aditem-main--top--left">37136 Waake</div>
        <div class="price-shipping--price">15 €</div>
      </li>
      <li class="ad-listitem">
        <a href="/s-anzeige/f-zero-snes/3475833580-227-5678">
          <h2>F-Zero SNES Modul</h2>
        </a>
        <div class="price-shipping--price">20 €</div>
      </li>
    </ul>
    <a class="pagination-next" href="/s-seite:2/snes/k0">Weiter</a>
    """

    async def fake_fetch(_url: str) -> str:
        return html

    payload = runtime.SearchPayload({
        "query": "Snes",
        "include_review": True,
        "include_rejected": True,
    })
    result = asyncio.run(runtime.search_page(payload, fake_fetch))

    assert result["summary"]["fetched_listings"] == 2
    assert [item["id"] for item in result["listings"]] == ["3475838898", "3475833580"]
    assert result["pagination"]["stop_reason"] == "work_packet_complete"
    assert result["pagination"]["next_page"] == 1
    diagnostics = result["coverage_diagnostics"]
    assert diagnostics["extraction_strategy"] == "s_anzeige_link_windows"
    assert diagnostics["html_article_data_adid"] == 0
    assert diagnostics["html_s_anzeige_links"] == 2
    assert diagnostics["html_unique_s_anzeige_links"] == 2
    assert diagnostics["candidate_card_count"] == 2


def test_reported_results_without_candidates_is_not_empty_page():
    html = "<html><body><div>6.669 Ergebnisse</div></body></html>"

    async def fake_fetch(_url: str) -> str:
        return html

    payload = runtime.SearchPayload({"query": "Snes"})
    with pytest.raises(runtime.ParserLayoutError) as exc_info:
        asyncio.run(runtime.search_page(payload, fake_fetch))

    error = exc_info.value
    assert error.diagnostics["reported_total"] == 6669
    assert error.diagnostics["candidate_card_count"] == 0
    assert error.diagnostics["reason"] == "reported_total_without_candidates"


def test_truly_empty_page_can_end_as_verified_empty():
    async def fake_fetch(_url: str) -> str:
        return "<html><body>Keine Treffer</body></html>"

    payload = runtime.SearchPayload({"query": "Snes"})
    result = asyncio.run(runtime.search_page(payload, fake_fetch))
    assert result["pagination"]["complete"] is True
    assert result["pagination"]["stop_reason"] == "empty_page_verified"


def test_identity_marks_link_fallback_runtime():
    identity = runtime.identity()
    assert identity["version"] == "0.44.5.1"
    assert identity["runtime_module"] == "worker_runtime_v04451"
    assert identity["runtime_model"] == "direct-worker-stdlib-link-fallback-v1"
    assert identity["reference_version"] == "0.44.4"
