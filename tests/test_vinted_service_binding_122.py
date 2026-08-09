import asyncio
import json

from generic_parser import vinted_adapter


class FakeResponse:
    status = 200

    async def text(self):
        return json.dumps({
            "status": "ok",
            "component": "vinted-browser-poc",
            "revision": "test",
            "targetUrl": "https://www.vinted.de/catalog?search_text=Evercade",
            "enrichment": {"requested": 1, "ok": 1, "images": 1, "prices": 1, "descriptions": 1, "conditions": 1},
            "complete": True,
            "nextPage": None,
            "listings": [{
                "id": "vinted:123",
                "title": "Evercade Test",
                "url": "https://www.vinted.de/items/123-evercade-test",
                "price": 20,
                "condition": "Sehr gut",
                "image_url": "https://images.example/vinted-123.jpg",
                "description": "Komplett mit Hülle und Anleitung, sehr guter Zustand.",
                "detail_status": "ok",
                "detail_fields": ["image", "price", "description", "condition"],
            }],
        })


class FakeBinding:
    def __init__(self):
        self.urls = []

    async def fetch(self, url):
        self.urls.append(url)
        return FakeResponse()


def test_browser_search_uses_service_binding_and_preserves_detail_enrichment():
    async def scenario():
        binding = FakeBinding()
        token = vinted_adapter.set_vinted_browser_binding(binding)
        try:
            result = await vinted_adapter._fetch_browser_worker("Evercade", 0)
        finally:
            vinted_adapter.reset_vinted_browser_binding(token)
        assert result["status"] == "ok"
        assert result["strategy"] == "service-binding"
        assert result["enrichment"]["images"] == 1
        listing = result["listings"][0]
        assert listing["id"] == "vinted:123"
        assert listing["image_url"].endswith("vinted-123.jpg")
        assert listing["price"] == 20
        assert "Hülle" in listing["description"]
        assert listing["detail_enrichment"]["status"] == "ok"
        assert set(listing["detail_enrichment"]["fields"]) == {"image", "price", "description", "condition"}
        assert binding.urls[0].startswith("https://vinted-browser.internal/search?")
        assert "workers.dev" not in binding.urls[0]

    asyncio.run(scenario())


def test_missing_binding_fails_open_without_network_call():
    async def scenario():
        token = vinted_adapter.set_vinted_browser_binding(None)
        try:
            result = await vinted_adapter._fetch_browser_worker("Evercade", 0)
        finally:
            vinted_adapter.reset_vinted_browser_binding(token)
        assert result["status"] == "degraded"
        assert result["reason"] == "vinted_service_binding_unavailable"

    asyncio.run(scenario())
