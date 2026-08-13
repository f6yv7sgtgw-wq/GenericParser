"""1.9.5: Die anonyme Vinted-Blättertiefe ist ein natürliches Ende, kein Fehler."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import generic_parser.cloudflare_v0452 as transport
import generic_parser.vinted_adapter as vinted
from generic_parser.search_service_v0450 import SearchRequest

from test_release_160 import request_body


class _FakeResponse:
    def __init__(self, payload: dict):
        self.status = 200
        self._payload = payload

    async def text(self) -> str:
        return json.dumps(self._payload)


class _FakeBinding:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0

    async def fetch(self, url: str) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(self.payload)


EMPTY_PAGE = {"status": "empty", "reason": "no_public_listings_parsed", "targetUrl": "https://www.vinted.de/catalog?page=11", "browser": {"parseStrategy": "cards"}}


def _with_binding(payload: dict):
    return vinted.set_vinted_browser_binding(_FakeBinding(payload))


def test_an_empty_page_beyond_the_first_is_the_anonymous_depth_end():
    token = _with_binding(EMPTY_PAGE)
    try:
        result = asyncio.run(vinted._fetch_browser_worker("lemmings", 10))
    finally:
        vinted.reset_vinted_browser_binding(token)
    assert result["authoritative_empty"] is True
    assert result["status"] == "empty"
    assert result["reason"] == "vinted_anonymous_depth_reached"
    assert result["complete"] is True
    assert result["next_page"] is None


def test_an_empty_first_page_still_degrades_visibly():
    # Ein Markup-Bruch soll auf Seite 0 sichtbar degradieren, nicht als
    # "keine Treffer" durchgehen.
    token = _with_binding(EMPTY_PAGE)
    try:
        result = asyncio.run(vinted._fetch_browser_worker("lemmings", 0))
    finally:
        vinted.reset_vinted_browser_binding(token)
    assert "authoritative_empty" not in result
    assert result["status"] == "degraded"
    assert result["reason"] == "no_public_listings_parsed"


def test_the_depth_end_skips_the_pointless_public_web_fallback(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        raise AssertionError("public-web fallback must not run at the depth end")

    monkeypatch.setattr(vinted, "_bootstrap_session", forbidden)
    token = _with_binding(EMPTY_PAGE)
    try:
        result = asyncio.run(vinted.search_vinted("lemmings", page=10))
    finally:
        vinted.reset_vinted_browser_binding(token)
    assert result["status"] == "empty"
    assert result["reason"] == "vinted_anonymous_depth_reached"


def test_the_depth_end_gets_no_retries_and_completes_the_source(monkeypatch):
    calls: list[int] = []

    async def search_page(payload, _request):
        calls.append(payload.page)
        return {
            "listings": [],
            "pagination": {"current_page": payload.page, "next_page": None, "complete": True, "source": "vinted"},
            "source_status": {
                "vinted": {"enabled": True, "status": "empty", "reason": "vinted_anonymous_depth_reached"}
            },
        }

    service = SimpleNamespace(SearchRequest=SearchRequest, search_page=search_page)
    monkeypatch.setattr(transport, "load_service", lambda: service)
    response = TestClient(transport.app).post(
        "/api/module/v2/search", json=request_body(sources=["vinted"])
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["stop_reason"] == "batch_complete"
    vinted_status = payload["results"][0]["sources"]["vinted"]
    assert vinted_status["status"] == "empty"
    assert "retry" not in vinted_status
    assert payload["results"][0]["source_complete"] is True
    assert len(calls) == 1  # genau ein Paket, keine erneuten Anläufe
