from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNTIME_PATH = ROOT / "src/generic_parser/worker_runtime_v0445.py"
ENTRY_PATH = ROOT / "src/generic_parser/cloudflare_worker.py"


def _load_runtime():
    spec = importlib.util.spec_from_file_location("worker_runtime_v0445_test", RUNTIME_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = _load_runtime()


def test_direct_worker_has_no_heavy_live_imports():
    source = ENTRY_PATH.read_text(encoding="utf-8")
    runtime_source = RUNTIME_PATH.read_text(encoding="utf-8")
    combined = source + "\n" + runtime_source
    forbidden = (
        "import importlib",
        "from fastapi",
        "import fastapi",
        "from pydantic",
        "import pydantic",
        "import asgi",
        "import httpx",
        "from generic_parser",
    )
    for marker in forbidden:
        assert marker not in combined


def test_empty_optional_fields_create_no_optional_criteria():
    payload = runtime.SearchPayload({"query": "Evercade"})
    listing = {
        "title": "Evercade Tomb Raider Collection",
        "price": 30.0,
        "result_info": {
            "offer_type": "Spiel/Cartridge",
            "condition": "Zustand offen",
            "scope": "Einzelangebot",
        },
    }
    evaluation = runtime._evaluate(listing, payload)
    assert evaluation["color"] == "green"
    assert [item["name"] for item in evaluation["criteria"]] == ["Suchbegriff"]


def test_active_required_excluded_and_price_rules_match_0444_contract():
    payload = runtime.SearchPayload({
        "query": "Evercade",
        "required_terms": ["cartridge"],
        "excluded_terms": ["defekt"],
        "max_price": 40,
    })
    listing = {
        "title": "Evercade Cartridge Collection",
        "price": 35.0,
        "result_info": {
            "offer_type": "Spiel/Cartridge",
            "condition": "Zustand offen",
            "scope": "Einzelangebot",
        },
    }
    evaluation = runtime._evaluate(listing, payload)
    assert evaluation["color"] == "green"
    assert {item["name"] for item in evaluation["criteria"]} == {
        "Suchbegriff", "Pflichtbegriffe", "Ausschlussbegriffe", "Maximalpreis"
    }


def test_hard_rule_violation_is_red():
    payload = runtime.SearchPayload({
        "query": "Evercade",
        "required_terms": ["cartridge"],
        "max_price": 40,
    })
    listing = {
        "title": "Evercade Konsole",
        "price": 60.0,
        "result_info": {
            "offer_type": "Konsole/Handheld",
            "condition": "Zustand offen",
            "scope": "Einzelangebot",
        },
    }
    evaluation = runtime._evaluate(listing, payload)
    assert evaluation["color"] == "red"
    assert evaluation["decision"] == "reject"


def test_page_contract_with_fake_html_and_next_link():
    html = """
    <div>2 Ergebnisse</div>
    <article data-adid="1001" data-href="/s-anzeige/evercade-cartridge/1001">
      <a href="/s-anzeige/evercade-cartridge/1001"><h2>Evercade Cartridge Collection</h2></a>
      <div class="aditem-main--top--left">37136 Waake</div>
      <div class="aditem-main--top--right">Heute</div>
      <div class="aditem-main--middle--description">Vollständig</div>
      <div class="price-shipping--price">35 €</div>
    </article>
    <article data-adid="1002" data-href="/s-anzeige/evercade-cartridge-2/1002">
      <a href="/s-anzeige/evercade-cartridge-2/1002"><h2>Evercade Cartridge 2</h2></a>
      <div class="price-shipping--price">30 €</div>
    </article>
    <a class="pagination-next" href="/s-seite:2/evercade/k0">Weiter</a>
    """

    async def fake_fetch(_url: str) -> str:
        return html

    payload = runtime.SearchPayload({
        "query": "Evercade",
        "required_terms": ["cartridge"],
        "include_review": True,
        "include_rejected": True,
    })
    result = asyncio.run(runtime.search_page(payload, fake_fetch))
    assert result["summary"]["fetched_listings"] == 2
    assert result["summary"]["visible_listings"] == 2
    assert result["pagination"]["next_page"] == 1
    assert result["pagination"]["next_link_found"] is True
    assert result["summary"]["data_consistent"] is True
    assert all(item["traffic_light"]["color"] == "green" for item in result["listings"])


def test_identity_marks_direct_runtime():
    identity = runtime.identity()
    assert identity["version"] == "0.44.5"
    assert identity["runtime_model"] == "direct-worker-stdlib-v1"
    assert identity["reference_version"] == "0.44.4"
