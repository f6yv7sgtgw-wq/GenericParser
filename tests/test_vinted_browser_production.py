import asyncio

import generic_parser.vinted_adapter as vinted


def test_browser_item_is_normalized_for_multisource_pipeline():
    raw = {
        "id": "vinted:12345",
        "title": "Evercade Bitmap Brothers Collection 2",
        "url": "https://www.vinted.de/items/12345-evercade-bitmap-brothers",
        "price": 20,
        "condition": "Sehr gut",
    }
    item = vinted._normalize_browser_item(raw, "Evercade")
    assert item is not None
    assert item["id"] == "vinted:12345"
    assert item["source"] == "vinted"
    assert item["source_label"] == "Vinted"
    assert item["price"] == 20.0
    assert item["result_info"]["condition"] == "wie neu"


def test_search_vinted_prefers_browser_worker_without_public_web_fallback(monkeypatch):
    calls = {"browser": 0, "bootstrap": 0}

    async def fake_browser(query, page):
        calls["browser"] += 1
        return {
            "listings": [{
                "id": "vinted:9",
                "title": "Evercade Interplay Collection 1",
                "url": "https://www.vinted.de/items/9-evercade-interplay",
                "price": 25.0,
                "source": "vinted",
                "source_label": "Vinted",
                "result_info": {"condition": "wie neu"},
            }],
            "status": "ok",
            "strategy": "browser-run-worker",
            "http_status": 200,
            "complete": True,
            "next_page": None,
        }

    async def forbidden_bootstrap(client):
        calls["bootstrap"] += 1
        raise AssertionError("public-web fallback must not run when Browser worker succeeds")

    monkeypatch.setattr(vinted, "_fetch_browser_worker", fake_browser)
    monkeypatch.setattr(vinted, "_bootstrap_session", forbidden_bootstrap)
    result = asyncio.run(vinted.search_vinted("Evercade", page=0))
    assert result["status"] == "ok"
    assert result["strategy"] == "browser-run-worker"
    assert len(result["listings"]) == 1
    assert calls == {"browser": 1, "bootstrap": 0}


def test_browser_failure_remains_fail_open_and_can_fall_back(monkeypatch):
    async def fake_browser(query, page):
        return {"listings": [], "status": "degraded", "reason": "temporary", "http_status": 502, "strategy": "service-binding"}

    async def fake_bootstrap(client):
        return {"status": "ok", "http_status": 200, "reason": None, "cookie_count": 0}

    async def fake_html(client, query, page):
        return {"listings": [{"id": "vinted:77", "title": "Evercade", "source": "vinted"}], "status": "ok", "http_status": 200, "reason": None, "url": "https://www.vinted.de/catalog", "strategy": "session+html"}

    monkeypatch.setattr(vinted, "_fetch_browser_worker", fake_browser)
    monkeypatch.setattr(vinted, "_bootstrap_session", fake_bootstrap)
    monkeypatch.setattr(vinted, "_fetch_html", fake_html)
    result = asyncio.run(vinted.search_vinted("Evercade", page=0))
    assert result["status"] == "ok"
    assert result["strategy"] == "service-binding-fallback+session+html"
    assert result["browser_fallback"]["reason"] == "temporary"
