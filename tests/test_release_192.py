"""1.9.2: Blockiertes Vinted wird begrenzt erneut versucht statt endgültig beendet."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import generic_parser.cloudflare_v0452 as transport
from generic_parser.module_api_v2 import (
    VINTED_BLOCK_RETRY_LIMIT,
    VINTED_COOLDOWN_SECONDS,
    VINTED_RETRY_COOLDOWN_SCHEDULE,
    _advance_state,
)
from generic_parser.search_service_v0450 import SearchRequest

from test_release_160 import fake_service, request_body


def scripted_service(script: list[str]):
    """Ein Vinted, das nach Drehbuch antwortet: 'blocked' oder 'ok'."""

    calls: list[str] = []

    async def search_page(payload, _request):
        kind = script[min(len(calls), len(script) - 1)]
        calls.append(kind)
        if kind == "blocked":
            return {
                "listings": [],
                "pagination": {
                    "current_page": payload.page,
                    "next_page": None,
                    "complete": True,
                    "source": payload.source,
                },
                "source_status": {
                    payload.source: {
                        "enabled": True,
                        "status": "blocked",
                        "http_status": 403,
                        "reason": "bootstrap:vinted_session_bootstrap_access_limited",
                    }
                },
            }
        inner = fake_service(next_page=None)
        return await inner.search_page(payload, _request)

    return SimpleNamespace(SearchRequest=SearchRequest, search_page=search_page), calls


def _post(client, body):
    response = client.post("/api/module/v2/search", json=body)
    assert response.status_code == 200
    return response.json()


def test_a_blocked_vinted_gets_a_retry_instead_of_a_final_end(monkeypatch):
    service, calls = scripted_service(["blocked", "ok"])
    monkeypatch.setattr(transport, "load_service", lambda: service)
    client = TestClient(transport.app)
    body = request_body(sources=["vinted"])

    first = _post(client, body)
    assert first["status"] == "partial"
    assert first["continuation_token"]
    assert first["results"][0]["source_complete"] is False
    retry = first["results"][0]["sources"]["vinted"]["retry"]
    assert retry == {
        "attempt": 1,
        "limit": VINTED_BLOCK_RETRY_LIMIT,
        "cooldown_seconds": VINTED_RETRY_COOLDOWN_SCHEDULE[0],
    }
    # Der Wartehinweis nutzt die längere Retry-Abklingzeit.
    assert first["pacing"]["source"] == "vinted"
    assert first["pacing"]["wait_ms"] > int(VINTED_COOLDOWN_SECONDS * 1000)

    resumed = _post(client, {**body, "continuation_token": first["continuation_token"]})
    assert resumed["status"] == "complete"
    assert resumed["results"][0]["sources"]["vinted"]["status"] == "ok"
    assert calls == ["blocked", "ok"]


def test_the_same_page_is_retried_not_skipped(monkeypatch):
    service, _ = scripted_service(["blocked", "ok"])
    monkeypatch.setattr(transport, "load_service", lambda: service)
    client = TestClient(transport.app)
    body = request_body(sources=["vinted"])
    first = _post(client, body)
    resumed = _post(client, {**body, "continuation_token": first["continuation_token"]})
    assert resumed["results"][0]["page"] == first["results"][0]["page"]


def test_after_the_last_attempt_the_source_ends_honestly_blocked(monkeypatch):
    service, calls = scripted_service(["blocked", "blocked", "blocked"])
    monkeypatch.setattr(transport, "load_service", lambda: service)
    client = TestClient(transport.app)
    body = request_body(sources=["vinted"])

    result = _post(client, body)
    for attempt in range(VINTED_BLOCK_RETRY_LIMIT):
        assert result["status"] == "partial"
        response = client.post(
            "/api/module/v2/search",
            json={**body, "continuation_token": result["continuation_token"]},
        )
        # Der letzte gescheiterte Anlauf ist zugleich "alle Quellen gescheitert"
        # und behält dessen bestehende 502-Abbildung samt vollem v2-Body.
        expected = 502 if attempt == VINTED_BLOCK_RETRY_LIMIT - 1 else 200
        assert response.status_code == expected
        result = response.json()

    assert result["status"] == "complete"
    assert result["stop_reason"] == "all_sources_failed"
    assert result["continuation_token"] is None
    vinted = result["results"][0]["sources"]["vinted"]
    assert vinted["status"] == "blocked"
    assert "retry" not in vinted
    assert len(calls) == 1 + VINTED_BLOCK_RETRY_LIMIT


def test_a_successful_resume_resets_the_retry_budget(monkeypatch):
    service, calls = scripted_service(["blocked", "ok"])
    monkeypatch.setattr(transport, "load_service", lambda: service)
    client = TestClient(transport.app)
    body = request_body(sources=["vinted"])
    first = _post(client, body)
    resumed = _post(client, {**body, "continuation_token": first["continuation_token"]})
    assert resumed["status"] == "complete"
    # Kein retry-Feld mehr am erfolgreichen Paket.
    assert "retry" not in resumed["results"][0]["sources"]["vinted"]


def test_other_sources_keep_rotating_while_the_retry_waits():
    request = SimpleNamespace(
        searches=[SimpleNamespace(sources=["kleinanzeigen", "vinted", "ebay"])]
    )
    state = {
        "search_index": 0,
        "source_index": 1,  # Vinted hat gerade das blockierte Paket geliefert
        "page": 5,
        "pages_processed": 0,
        "listings_returned": 0,
        "searches_complete": 0,
        "sources_complete": 0,
        "failed_sources": 0,
        "degraded": True,
        "source_retry_counts": {"vinted": 1},
    }
    updated, _, _ = _advance_state(
        state,
        request,
        page_complete=False,
        next_page=5,
        failed=False,
        degraded=True,
        listings=0,
        now=1000.0,
    )
    assert updated["source_index"] == 2  # eBay macht weiter

    # Nach der normalen Schonfrist (20 s) ist Vinted noch NICHT dran …
    later, _, _ = _advance_state(
        updated,
        request,
        page_complete=False,
        next_page=1,
        failed=False,
        degraded=False,
        listings=25,
        now=1000.0 + VINTED_COOLDOWN_SECONDS + 5,
    )
    assert later["source_index"] == 0  # Kleinanzeigen, nicht Vinted

    # … erst nach der Retry-Abklingzeit des ersten Anlaufs (60 s).
    ready, _, _ = _advance_state(
        later,
        request,
        page_complete=False,
        next_page=1,
        failed=False,
        degraded=False,
        listings=7,
        now=1000.0 + VINTED_RETRY_COOLDOWN_SCHEDULE[0] + 1,
    )
    assert ready["source_index"] == 1
    assert ready["page"] == 5  # dieselbe Seite wird erneut versucht
