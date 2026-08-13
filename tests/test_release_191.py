"""1.9.1: Vinted-Abklingzeit, ehrliches Quellen-Ende, Schreibvarianten, Rescore."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import generic_parser.cloudflare_v0452 as transport
from generic_parser.module_api_v2 import (
    VINTED_COOLDOWN_SECONDS,
    _advance_state,
)
from generic_parser.relevance import _close_variant
from generic_parser.search_service_v0450 import SearchRequest
from generic_parser.vinted_enrichment import _decorate

from test_release_160 import fake_service, request_body


SOURCES = ["kleinanzeigen", "vinted", "ebay"]


def _request(sources: list[str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(searches=[SimpleNamespace(sources=sources or SOURCES)])


def _fresh_state() -> dict:
    return {
        "search_index": 0,
        "source_index": 0,
        "page": 0,
        "pages_processed": 0,
        "listings_returned": 0,
        "searches_complete": 0,
        "sources_complete": 0,
        "failed_sources": 0,
        "degraded": False,
    }


def _advance(state: dict, *, now: float, request=None, page_complete: bool = False) -> dict:
    updated, _, _ = _advance_state(
        state,
        request or _request(),
        page_complete=page_complete,
        next_page=None if page_complete else int(state.get("page") or 0) + 1,
        failed=False,
        degraded=False,
        listings=25,
        now=now,
    )
    return updated


# --- Vinted-Abklingzeit in der Rotation ------------------------------------


def test_vinted_skips_its_turn_while_the_cooldown_runs():
    state = _fresh_state()
    state = _advance(state, now=0.0)            # Kleinanzeigen → Vinted ist dran
    assert SOURCES[state["source_index"]] == "vinted"
    state = _advance(state, now=5.0)            # Vinted → eBay
    assert SOURCES[state["source_index"]] == "ebay"
    state = _advance(state, now=10.0)           # eBay → Vinted wäre dran, wartet aber
    assert SOURCES[state["source_index"]] == "kleinanzeigen"
    assert "pacing" not in state


def test_vinted_returns_once_the_cooldown_has_elapsed():
    state = _fresh_state()
    state = _advance(state, now=0.0)
    state = _advance(state, now=5.0)            # Vinted-Paket bei t=5
    state = _advance(state, now=10.0)           # eBay; Vinted wartet
    state = _advance(state, now=5.0 + VINTED_COOLDOWN_SECONDS + 1)
    assert SOURCES[state["source_index"]] == "vinted"


def test_vinted_resumes_at_its_own_page_after_waiting():
    state = _fresh_state()
    state = _advance(state, now=0.0)
    state = _advance(state, now=5.0)            # Vinted stand danach auf Seite 1
    state = _advance(state, now=10.0)
    state = _advance(state, now=40.0)
    assert SOURCES[state["source_index"]] == "vinted"
    assert state["page"] == 1


def test_only_vinted_left_yields_a_pacing_hint_instead_of_starvation():
    state = _fresh_state()
    state["source_index"] = 1
    state["sources_done"] = ["kleinanzeigen", "ebay"]
    state["page"] = 3
    state = _advance(state, now=100.0)
    assert SOURCES[state["source_index"]] == "vinted"
    assert state["page"] == 4
    assert state["pacing"]["source"] == "vinted"
    assert 0 < state["pacing"]["wait_ms"] <= int(VINTED_COOLDOWN_SECONDS * 1000)


def test_older_tokens_without_timestamps_keep_working():
    state = _fresh_state()
    assert "source_last_at" not in state
    updated = _advance(state, now=50.0)
    assert updated["source_last_at"]["kleinanzeigen"] == 50.0


# --- Additives Paketfeld source_complete und pacing im v2-Vertrag -----------


def test_v2_packet_reports_whether_its_source_completed(monkeypatch):
    monkeypatch.setattr(transport, "load_service", lambda: fake_service())
    response = TestClient(transport.app).post("/api/module/v2/search", json=request_body())
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["source_complete"] is True
    assert "pacing" not in payload


def test_a_vinted_only_continuation_carries_the_pacing_hint(monkeypatch):
    monkeypatch.setattr(transport, "load_service", lambda: fake_service(next_page=1))
    body = request_body(sources=["vinted"])
    response = TestClient(transport.app).post("/api/module/v2/search", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["source_complete"] is False
    assert payload["continuation_token"]
    assert payload["pacing"]["source"] == "vinted"
    assert 0 < payload["pacing"]["wait_ms"] <= int(VINTED_COOLDOWN_SECONDS * 1000)


# --- Schreibvarianten (relevance-v2) ----------------------------------------


def test_close_variants_cover_plural_and_typo_but_not_lookalikes():
    assert _close_variant("lemmings", "lemminge")
    assert _close_variant("tribes", "tribess")
    assert not _close_variant("mario", "wario")   # zu kurz für Toleranz
    assert not _close_variant("kart", "karte")    # zu kurz für Toleranz
    assert not _close_variant("lemmings", "hemminge")  # Anfangsbuchstabe zählt
    assert not _close_variant("lemmings", "lemmingsen")  # zwei Zeichen entfernt


# --- Neubewertung nach Vinted-Anreicherung ----------------------------------


def test_enrichment_rescore_applies_the_relevance_rule_like_the_main_search():
    payload = SearchRequest(query="lemmings snes")
    listing = {
        "id": "vinted:1",
        "source": "vinted",
        "title": "Donkey Kong Country SNES",
        "description": "Super Nintendo Spiel",
        "price": {"raw": "30 €", "amount": 30.0},
    }
    decorated = _decorate(listing, payload)
    assert decorated["relevance"]["verdict"] == "review"
    assert "lemmings" in decorated["relevance"]["missing_terms"]
    assert any(
        c.get("name") == "Relevanz" for c in decorated["traffic_light"]["criteria"]
    )
    assert "fehlt" in decorated["match"]["reason"]
