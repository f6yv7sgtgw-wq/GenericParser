"""1.9.3: Retry-Staffel 60/120 s, Zeitraum-Kriterium, additives max_age_days."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

import generic_parser.cloudflare_v0452 as transport
from generic_parser.listing_age import apply_age_evaluation, evaluate_listing_age
from generic_parser.module_api import ModuleSearchProfile
from generic_parser.module_api_v2 import (
    VINTED_RETRY_COOLDOWN_SCHEDULE,
    _advance_state,
)
from generic_parser.search_service_v0450 import SearchRequest, _decorate_listing

from test_release_160 import request_body
from test_release_192 import scripted_service


NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)


# --- Retry-Staffel: 60 s, dann 120 s, danach Abbruch ------------------------


def test_the_second_attempt_waits_twice_as_long(monkeypatch):
    service, _ = scripted_service(["blocked", "blocked", "blocked"])
    monkeypatch.setattr(transport, "load_service", lambda: service)
    client = TestClient(transport.app)
    body = request_body(sources=["vinted"])

    first = client.post("/api/module/v2/search", json=body).json()
    assert first["results"][0]["sources"]["vinted"]["retry"]["cooldown_seconds"] == 60.0
    assert first["pacing"]["wait_ms"] <= 60_000

    second = client.post(
        "/api/module/v2/search",
        json={**body, "continuation_token": first["continuation_token"]},
    ).json()
    assert second["results"][0]["sources"]["vinted"]["retry"]["cooldown_seconds"] == 120.0
    assert 60_000 < second["pacing"]["wait_ms"] <= 120_000

    final = client.post(
        "/api/module/v2/search",
        json={**body, "continuation_token": second["continuation_token"]},
    )
    assert final.json()["status"] == "complete"


def test_the_rotation_waits_the_scheduled_cooldown_per_attempt():
    request = SimpleNamespace(
        searches=[SimpleNamespace(sources=["kleinanzeigen", "vinted", "ebay"])]
    )
    state = {
        "search_index": 0,
        "source_index": 1,
        "page": 5,
        "pages_processed": 0,
        "listings_returned": 0,
        "searches_complete": 0,
        "sources_complete": 0,
        "failed_sources": 0,
        "degraded": True,
        "source_retry_counts": {"vinted": 2},  # zweiter Anlauf steht aus
    }
    updated, _, _ = _advance_state(
        state, request,
        page_complete=False, next_page=5, failed=False, degraded=True, listings=0,
        now=1000.0,
    )
    # Nach 61 s (erste Stufe) wäre Vinted beim ersten Anlauf dran gewesen —
    # beim zweiten Anlauf gilt die zweite Stufe (120 s).
    later, _, _ = _advance_state(
        updated, request,
        page_complete=False, next_page=1, failed=False, degraded=False, listings=25,
        now=1000.0 + VINTED_RETRY_COOLDOWN_SCHEDULE[0] + 1,
    )
    assert later["source_index"] != 1
    ready, _, _ = _advance_state(
        later, request,
        page_complete=False, next_page=1, failed=False, degraded=False, listings=7,
        now=1000.0 + VINTED_RETRY_COOLDOWN_SCHEDULE[1] + 1,
    )
    assert ready["source_index"] == 1


# --- Zeitraum-Kriterium ------------------------------------------------------


def test_a_listing_within_the_window_passes():
    posted = (NOW - timedelta(days=30)).isoformat()
    assert evaluate_listing_age(posted, 90, now=NOW) is None


def test_a_listing_outside_the_window_is_flagged():
    posted = (NOW - timedelta(days=120)).isoformat()
    violation = evaluate_listing_age(posted, 90, now=NOW)
    assert violation["age_days"] == 120
    assert violation["max_age_days"] == 90
    assert "120 Tage alt" in violation["reason"]


def test_listings_without_a_date_pass_deliberately():
    # Betrifft vor allem Vinted: Ein Filter, der nichts prüfen kann, darf
    # nichts aussortieren.
    assert evaluate_listing_age(None, 90, now=NOW) is None
    assert evaluate_listing_age("", 90, now=NOW) is None
    assert evaluate_listing_age("kein Datum", 90, now=NOW) is None


def test_without_a_window_nothing_is_checked():
    old = (NOW - timedelta(days=3000)).isoformat()
    assert evaluate_listing_age(old, None, now=NOW) is None
    assert evaluate_listing_age(old, 0, now=NOW) is None


def test_z_suffix_and_naive_datetimes_are_understood():
    assert evaluate_listing_age("2026-08-01T10:00:00.000Z", 90, now=NOW) is None
    naive = datetime(2020, 1, 1, 12, 0, 0)
    assert evaluate_listing_age(naive, 90, now=NOW) is not None


def test_the_violation_turns_the_light_red_but_keeps_the_listing():
    green = {
        "color": "green", "label": "🟢 Passend", "score": 90,
        "decision": "accept", "reason": "Alle Kriterien erfüllt",
        "criteria": [], "active_criteria": 0,
    }
    violation = evaluate_listing_age(
        (NOW - timedelta(days=200)).isoformat(), 90, now=NOW
    )
    result = apply_age_evaluation(green, violation)
    assert result["color"] == "red"
    assert result["decision"] == "reject"
    criterion = result["criteria"][-1]
    assert criterion["name"] == "Zeitraum"
    assert criterion["hard"] is True
    assert apply_age_evaluation(green, None) == green


def test_decorated_listings_respect_the_window():
    payload = SearchRequest(query="lemmings snes", max_age_days=90)
    old = _decorate_listing(
        {
            "title": "Lemmings SNES PAL",
            "posted_at": "2024-08-07T09:48:03.000Z",
            "price": {"raw": "30 €", "amount": 30.0},
        },
        payload,
    )
    assert old["traffic_light"]["color"] == "red"
    assert any(c["name"] == "Zeitraum" for c in old["traffic_light"]["criteria"])

    undated = _decorate_listing(
        {
            "title": "Lemmings SNES PAL",
            "price": {"raw": "30 €", "amount": 30.0},
        },
        payload,
    )
    assert all(c["name"] != "Zeitraum" for c in undated["traffic_light"]["criteria"])


# --- Additives Vertragsfeld --------------------------------------------------


def test_the_v2_filter_is_additive_and_defaults_to_all(monkeypatch):
    captured: list = []

    async def search_page(payload, _request):
        captured.append(getattr(payload, "max_age_days", "missing"))
        from test_release_160 import fake_service

        return await fake_service().search_page(payload, _request)

    service = SimpleNamespace(SearchRequest=SearchRequest, search_page=search_page)
    monkeypatch.setattr(transport, "load_service", lambda: service)
    client = TestClient(transport.app)

    without = request_body()
    assert client.post("/api/module/v2/search", json=without).status_code == 200
    with_window = request_body()
    with_window["search"]["filters"]["max_age_days"] = 90
    assert client.post("/api/module/v2/search", json=with_window).status_code == 200

    assert captured == [None, 90]


def test_the_v1_profile_forwards_the_window_only_when_set():
    with_window = ModuleSearchProfile(query="lemmings snes", max_age_days=90)
    assert with_window.to_legacy_payload()["max_age_days"] == 90
    without = ModuleSearchProfile(query="lemmings snes")
    assert "max_age_days" not in without.to_legacy_payload()
