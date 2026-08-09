import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import generic_parser.vinted_adapter as vinted_adapter
import generic_parser.vinted_enrichment as vinted_enrichment
from generic_parser.cloudflare_v0452 import app
from generic_parser.module_api import DebugTrace, ModuleDebugOptions, ModulePageRequest, ModuleSearchProfile, module_response_from_legacy
from generic_parser.release_identity import BUILD_ID, VERSION
from generic_parser.search_service_v0450 import SearchRequest


ROOT = Path(__file__).resolve().parents[1]


def test_release_132_background_feature_remains_active_in_current_release():
    metadata = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    public = json.loads((ROOT / "cloudflare/public/release-identity.json").read_text(encoding="utf-8"))
    assert metadata["version"] == VERSION
    assert metadata["build_id"] == BUILD_ID
    assert metadata["sources"]["vinted"]["background_batch_size"] == 3
    assert metadata["sources"]["vinted"]["main_search_blocked"] is False
    assert public["version"] == VERSION
    assert public["build_id"] == BUILD_ID


class DetailResponse:
    status = 200

    async def text(self):
        return json.dumps(
            {
                "status": "ok",
                "component": "vinted-browser-poc",
                "revision": "test-132",
                "elapsedMs": 1234,
                "enrichment": {
                    "requested": 1,
                    "ok": 1,
                    "images": 1,
                    "prices": 1,
                    "descriptions": 1,
                    "conditions": 1,
                },
                "listings": [
                    {
                        "id": "vinted:123",
                        "title": "Evercade Test",
                        "url": "https://www.vinted.de/items/123-evercade-test",
                        "price": 20,
                        "condition": "Sehr gut",
                        "image_url": "https://images.example/vinted-123.jpg",
                        "description": "Komplett mit Hülle und Anleitung.",
                        "detail_status": "ok",
                        "detail_fields": ["image", "price", "description", "condition"],
                    }
                ],
            }
        )


class DetailBinding:
    def __init__(self):
        self.urls = []

    async def fetch(self, url):
        self.urls.append(url)
        return DetailResponse()


def test_private_service_binding_enriches_one_three_item_batch():
    async def scenario():
        binding = DetailBinding()
        token = vinted_adapter.set_vinted_browser_binding(binding)
        try:
            result = await vinted_adapter.enrich_vinted_details(
                [
                    {
                        "id": "vinted:123",
                        "title": "Evercade Test",
                        "url": "https://www.vinted.de/items/123-evercade-test",
                        "source_query": "Evercade",
                    }
                ]
            )
        finally:
            vinted_adapter.reset_vinted_browser_binding(token)
        assert result["status"] == "ok"
        assert result["strategy"] == "service-binding-deferred-detail"
        assert result["listings"][0]["detail_enrichment"]["status"] == "ok"
        assert result["listings"][0]["price"] == 20
        assert binding.urls[0].startswith("https://vinted-browser.internal/enrich?")
        assert "item=https%3A%2F%2Fwww.vinted.de%2Fitems%2F123-evercade-test" in binding.urls[0]
        assert "workers.dev" not in binding.urls[0]

    asyncio.run(scenario())


def test_deferred_detail_validation_blocks_ssrf_and_oversized_batches():
    with pytest.raises(ValueError, match="canonical"):
        asyncio.run(
            vinted_adapter.enrich_vinted_details(
                [{"id": "vinted:123", "url": "https://example.invalid/items/123"}]
            )
        )
    rows = [
        {"id": f"vinted:{number}", "url": f"https://www.vinted.de/items/{number}-test"}
        for number in range(1, 5)
    ]
    with pytest.raises(ValueError, match="limit 3"):
        asyncio.run(vinted_adapter.enrich_vinted_details(rows))
    with pytest.raises(ValueError, match="canonical"):
        asyncio.run(
            vinted_adapter.enrich_vinted_details(
                [{"id": "vinted:123", "url": "https://www.vinted.de/items/123-test?redirect=1"}]
            )
        )


def test_background_merge_recalculates_price_dependent_scoring(monkeypatch):
    async def fake_details(listings):
        return {
            "status": "ok",
            "strategy": "service-binding-deferred-detail",
            "elapsed_ms": 900,
            "listings": [
                {
                    **listings[0],
                    "price": 99,
                    "price_raw": "99 €",
                    "image_url": "https://images.example/item.jpg",
                    "description": "Komplett und sehr gut erhalten.",
                    "result_info": {"condition": "wie neu"},
                    "detail_enrichment": {
                        "status": "ok",
                        "fields": ["image", "price", "description", "condition"],
                    },
                }
            ],
        }

    monkeypatch.setattr(vinted_enrichment, "enrich_vinted_details", fake_details)
    payload = SearchRequest.model_validate(
        {"mode": "live", "query": "Evercade Test", "max_price": 30, "page": 0, "source": "vinted"}
    )
    original = {
        "id": "vinted:123",
        "title": "Evercade Test",
        "url": "https://www.vinted.de/items/123-evercade-test",
        "source": "vinted",
        "price": None,
        "image_url": None,
        "description": None,
        "detail_enrichment": {"status": "skipped_budget", "fields": []},
        "result_info": {"condition": "Zustand offen", "scope": "Einzelangebot", "offer_type": "Produkt"},
    }
    result = asyncio.run(vinted_enrichment.enrich_vinted_batch([original], payload))
    listing = result["listings"][0]
    assert result["complete"] == 1
    assert listing["price"] == 99
    assert listing["match"]["decision"] == "reject"
    assert listing["traffic_light"]["color"] == "red"
    assert listing["detail_enrichment"]["mode"] == "background-batch"


def test_public_background_endpoint_is_separate_and_bounded():
    client = TestClient(app)
    search = {"mode": "live", "query": "Evercade", "page": 0, "source": "vinted"}
    rows = [
        {
            "id": f"vinted:{number}",
            "title": f"Evercade {number}",
            "url": f"https://www.vinted.de/items/{number}-evercade",
            "source": "vinted",
        }
        for number in range(1, 5)
    ]
    response = client.post("/api/vinted/enrich", json={"search": search, "listings": rows})
    assert response.status_code == 422
    assert response.json()["detail_batch_limit"] == 3
    assert response.headers["x-genericparser-contract"] == "generic-parser-module-v1"


def test_module_contract_preserves_vinted_description_and_detail_state():
    profile = ModuleSearchProfile(profile_id="evercade:test", display_name="Evercade Test", query="Evercade Test")
    request = ModulePageRequest(profile=profile, page=0, source="vinted")
    result = {
        "listings": [
            {
                "id": "vinted:123",
                "title": "Evercade Test",
                "url": "https://www.vinted.de/items/123-evercade-test",
                "source": "vinted",
                "source_label": "Vinted",
                "image_url": "https://images.example/item.jpg",
                "price": 20,
                "description": "Komplett mit Hülle.",
                "detail_enrichment": {"status": "ok", "fields": ["image", "price", "description"]},
            }
        ],
        "pagination": {"current_page": 0, "next_page": None, "complete": True, "source": "vinted", "unique_listings": 1},
        "summary": {"fetched_listings": 1, "visible_listings": 1, "hidden_by_filter": 0},
        "traffic_light_summary": {"green": 1, "yellow": 0, "red": 0},
    }
    response = module_response_from_legacy(result, request, DebugTrace(ModuleDebugOptions(), "test"))
    listing = response.listings[0]
    assert listing.source == "vinted"
    assert listing.source_label == "Vinted"
    assert listing.description == "Komplett mit Hülle."
    assert listing.detail_enrichment["status"] == "ok"


def test_capabilities_advertise_background_endpoint_for_module_clients():
    response = TestClient(app).get("/api/module/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][:2] == ["kleinanzeigen", "vinted"]
    assert "ebay" in payload["sources"]
    assert payload["vinted_detail_enrichment"]["background_endpoint"] == "/api/module/v1/vinted/enrich"
    assert payload["vinted_detail_enrichment"]["background_batch_limit"] == 3
    assert payload["vinted_detail_enrichment"]["blocks_search"] is False


def test_module_client_can_use_canonical_background_endpoint():
    response = TestClient(app).post(
        "/api/module/v1/vinted/enrich",
        json={
            "profile": {
                "profile_id": "snes:test",
                "display_name": "SNES Test",
                "query": "SNES Test",
                "max_price": 40,
            },
            "page": 0,
            "listings": [
                {
                    "id": "vinted:123",
                    "title": "SNES Test",
                    "url": "https://www.vinted.de/items/123-snes-test",
                    "source": "vinted",
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["request_format"] == "module-profile-v1"
    assert response.json()["contract"] == "generic-parser-module-v1"
    assert response.json()["listings"][0]["detail_enrichment"]["status"] == "background_error"


def test_browser_queue_is_non_blocking_serial_and_visible():
    script = (ROOT / "cloudflare/public/vinted-background-132.js").read_text(encoding="utf-8")
    html = (ROOT / "cloudflare/public/index.html").read_text(encoding="utf-8")
    poc = (ROOT / "pocs/vinted-browser/src/index.js").read_text(encoding="utf-8")
    assert "const BATCH_SIZE = 3" in script
    assert "queueMicrotask(() => void drain(token))" in script
    assert "api/vinted/enrich" in script
    assert "while (queue.length" in script
    assert "mainSearchBlocked: false" in script
    assert "done + cancelled >= totalQueued" in script
    assert "Vinted-Details nach Stopp beendet" in script
    assert "vinted-detail-state" in html
    assert "vinted-background-132.js" in html
    assert 'url.pathname==="/enrich"' in poc
    assert "Promise.all(candidates.map(item=>enrichOne(env,item)))" in poc
    assert "detail_batch_limit_exceeded" in poc
