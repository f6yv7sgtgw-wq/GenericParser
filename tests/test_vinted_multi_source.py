from __future__ import annotations

import asyncio

from bs4 import BeautifulSoup

from generic_parser import search_service_v0450 as service
from generic_parser.vinted_adapter import _from_cards, _from_structured_data, _normalize_api


def test_vinted_api_item_is_normalized_with_source_prefix():
    item = {
        "id": 12345,
        "title": "Evercade Interplay Collection 1",
        "url": "https://www.vinted.de/items/12345-evercade",
        "price": {"amount": "24.50"},
        "photo": {"url": "https://images.example/1.jpg"},
        "status": "Sehr gut",
        "user": {"city": "Berlin"},
    }
    result = _normalize_api(item, "Evercade Interplay Collection 1")
    assert result is not None
    assert result["id"] == "vinted:12345"
    assert result["source"] == "vinted"
    assert result["source_label"] == "Vinted"
    assert result["price"] == 24.5
    assert result["place"] == "Berlin"


def test_vinted_public_html_card_is_parsed():
    html = '''
    <article>
      <a href="/items/98765-evercade-tomb-raider" title="Evercade Tomb Raider Collection">
        <img src="https://images.example/tomb.jpg" alt="Evercade Tomb Raider Collection">
      </a>
      <span>Sehr gut</span><span>25,00 €</span>
    </article>
    '''
    rows = _from_cards(BeautifulSoup(html, "html.parser"), "Evercade")
    assert len(rows) == 1
    assert rows[0]["id"] == "vinted:98765"
    assert rows[0]["source"] == "vinted"
    assert rows[0]["price"] == 25.0
    assert rows[0]["result_info"]["condition"] == "wie neu"


def test_vinted_structured_product_is_parsed():
    html = '''<script type="application/ld+json">{
      "@type":"Product","name":"Evercade Bitmap Brothers","url":"https://www.vinted.de/items/456-evercade",
      "image":"https://images.example/456.jpg","offers":{"price":"19.50"},"itemCondition":"Sehr gut"
    }</script>'''
    rows = _from_structured_data(BeautifulSoup(html, "html.parser"), "Evercade")
    assert len(rows) == 1
    assert rows[0]["id"] == "vinted:456"
    assert rows[0]["price"] == 19.5


def test_runtime_identity_is_current_release_not_0450():
    assert service.VERSION == "1.1.1"
    assert service.BUILD_ID == "gp-111-20260808-1"


def test_auto_search_merges_kleinanzeigen_and_vinted(monkeypatch):
    async def fake_ka(payload, request):
        return {
            "listings": [{
                "id": "ka-1", "title": "Evercade Interplay Collection 1",
                "url": "https://www.kleinanzeigen.de/s-anzeige/example/1", "price": 30,
                "result_info": {"offer_type": "Produkt", "condition": "gebraucht", "scope": "Einzelangebot"},
                "match": {"score": 100, "decision": "accept", "listing_class": "Passender Treffer", "reason": "ok"},
                "traffic_light": {"color": "green"},
            }],
            "pagination": {"current_page": 0, "next_page": None, "complete": True, "source": "html-fallback", "unique_listings": 1},
            "summary": {"fetched_listings": 1, "visible_listings": 1, "hidden_by_filter": 0, "reported_total": 1},
            "traffic_light_summary": {"green": 1, "yellow": 0, "red": 0}, "generated_urls": [], "worker": {},
        }

    async def fake_vinted(query, page=0):
        return {
            "listings": [{"id": "vinted:2", "title": "Evercade Interplay Collection 1", "url": "https://www.vinted.de/items/2-evercade", "price": 25, "source": "vinted", "source_label": "Vinted", "result_info": {"offer_type": "Produkt", "condition": "wie neu", "scope": "Einzelangebot"}}],
            "next_page": None, "complete": True, "status": "ok", "http_status": 200, "reason": None,
            "strategy": "html", "url": "https://www.vinted.de/catalog?search_text=Evercade",
        }

    monkeypatch.setattr(service.reference, "search_page", fake_ka)
    monkeypatch.setattr(service, "search_vinted", fake_vinted)
    payload = service.SearchRequest.model_validate({"mode": "live", "query": "Evercade Interplay Collection 1", "page": 0, "source": "auto", "include_review": True, "include_rejected": True})
    result = asyncio.run(service.search_page(payload, None))
    assert len(result["listings"]) == 2
    assert {item.get("source") for item in result["listings"]} == {"kleinanzeigen", "vinted"}
    assert result["pagination"]["source"] == "multi-source"
    assert result["source_status"]["vinted"]["status"] == "ok"
    assert result["source_status"]["vinted"]["strategy"] == "html"
    assert result["worker"]["version"] == "1.1.1"


def test_vinted_failure_does_not_remove_kleinanzeigen(monkeypatch):
    async def fake_ka(payload, request):
        return {
            "listings": [{"id": "ka-1", "title": "Evercade", "url": "https://www.kleinanzeigen.de/s-anzeige/x/1", "match": {"decision": "review"}, "traffic_light": {"color": "yellow"}}],
            "pagination": {"next_page": None, "complete": True, "source": "html-fallback", "unique_listings": 1},
            "summary": {"fetched_listings": 1, "visible_listings": 1, "hidden_by_filter": 0},
            "traffic_light_summary": {"green": 0, "yellow": 1, "red": 0}, "generated_urls": [], "worker": {},
        }

    async def failed_vinted(query, page=0):
        return {"listings": [], "next_page": None, "complete": True, "status": "degraded", "http_status": 429, "reason": "vinted_access_limited", "strategy": "html", "url": "https://www.vinted.de/"}

    monkeypatch.setattr(service.reference, "search_page", fake_ka)
    monkeypatch.setattr(service, "search_vinted", failed_vinted)
    payload = service.SearchRequest.model_validate({"mode": "live", "query": "Evercade", "page": 0, "source": "auto"})
    result = asyncio.run(service.search_page(payload, None))
    assert len(result["listings"]) == 1
    assert result["listings"][0]["source"] == "kleinanzeigen"
    assert result["source_status"]["vinted"]["status"] == "degraded"
    assert result["source_status"]["vinted"]["http_status"] == 429
