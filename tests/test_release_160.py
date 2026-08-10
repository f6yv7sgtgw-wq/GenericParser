from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import generic_parser.cloudflare_v0452 as transport
from generic_parser.module_api_v2 import (
    MODULE_CONTRACT_V2,
    ContinuationExpired,
    decode_continuation,
    encode_continuation,
)
from generic_parser.release_identity import (
    API_CONTRACT,
    BUILD_ID,
    PREFERRED_MODULE_CONTRACT,
    SUPPORTED_MODULE_CONTRACTS,
    VERSION,
)
from generic_parser.search_service_v0450 import SearchRequest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def request_body(*, sources: list[str] | None = None, query: str = "Märklin H0/AC") -> dict:
    return {
        "contract": MODULE_CONTRACT_V2,
        "batch_id": "browser-test-1",
        "client": {"project_id": "genericparser-tests", "project_version": VERSION},
        "search": {
            "search_id": "search-äöü",
            "query": query,
            "sources": sources or ["ebay"],
            "criteria": {
                "required_terms": "Märklin, H0/AC, märklin",
                "excluded_terms": ["defekt", "nur OVP"],
                "model_patterns": [],
                "brands": ["Märklin"],
            },
            "filters": {
                "max_price": 90,
                "accept_bundles": False,
                "accept_incomplete": False,
                "include_auctions": False,
                "include_review": True,
                "include_rejected": True,
            },
            "location": {},
            "sort_by": "relevance",
        },
        "debug": {"enabled": False},
    }


def fake_service(*, next_page: int | None = None, status: str = "ok", http_status: int = 200):
    async def search_page(payload, _request):
        listings = []
        if status == "ok":
            listings = [
                {
                    "id": "ebay:v1|123|0",
                    "source": "ebay",
                    "title": "Märklin H0/AC Lok",
                    "url": "https://www.ebay.de/itm/123",
                    "image_url": "https://i.ebayimg.com/123.jpg",
                    "item_price": 40,
                    "shipping_cost": 5.49,
                    "total_price": 45.49,
                    "currency": "EUR",
                    "shipping_available": True,
                    "auction": False,
                    "listing_format": "FIXED_PRICE",
                    "seller": {"username": "must-not-leak"},
                    "product_classification": {
                        "code": "main_product",
                        "label": "Hauptprodukt",
                        "confidence": "high",
                        "ruleset": "product-classification-v1",
                    },
                    "match": {"decision": "accept", "reason": "Pflichtbegriffe gefunden", "score": 93},
                    "traffic_light": {"color": "green"},
                    "result_info": {"condition": "Gebraucht", "scope": "Einzelangebot"},
                }
            ]
        return {
            "listings": listings,
            "pagination": {
                "current_page": payload.page,
                "next_page": next_page,
                "complete": next_page is None,
                "source": payload.source,
            },
            "source_status": {
                payload.source: {
                    "enabled": True,
                    "status": status,
                    "http_status": http_status,
                    "reason": None if status == "ok" else "temporary",
                }
            },
        }

    return SimpleNamespace(SearchRequest=SearchRequest, search_page=search_page)


def test_release_identity_publishes_v2_additively():
    import generic_parser

    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert VERSION == "1.6.2"
    assert BUILD_ID == "gp-162-20260810-1"
    assert API_CONTRACT == "generic-parser-module-v1"
    assert PREFERRED_MODULE_CONTRACT == MODULE_CONTRACT_V2
    assert SUPPORTED_MODULE_CONTRACTS == (
        "generic-parser-module-v1",
        "generic-parser-module-v2",
    )
    assert generic_parser.__version__ == VERSION
    assert generic_parser.MODULE_CONTRACT_V2 == MODULE_CONTRACT_V2
    assert metadata["version"] == public["version"] == VERSION
    assert metadata["build_id"] == public["build_id"] == BUILD_ID
    assert metadata["status"] in {"release-candidate", "stable"}
    assert metadata["verification"]["production_acceptance"] in {"pending", "passed"}
    assert metadata["compatibility"]["module_v1_unchanged"] is True
    assert metadata["rollback_plan"] == {
        "last_stable_baseline": "1.6.1",
        "build_id": "gp-161-20260810-1",
    }


def test_v2_capabilities_and_v1_capabilities_are_both_available():
    client = TestClient(transport.app)
    v2 = client.get("/api/module/v2/capabilities")
    assert v2.status_code == 200
    assert v2.headers["X-GenericParser-Module-Contract"] == MODULE_CONTRACT_V2
    assert v2.headers["X-GenericParser-Supported-Contracts"] == (
        "generic-parser-module-v1,generic-parser-module-v2"
    )
    assert v2.json()["contract"] == MODULE_CONTRACT_V2
    assert v2.json()["persistent_server_jobs"] is False
    assert v2.json()["continuation"]["signed"] is True

    v1 = client.get("/api/module/v1/capabilities")
    assert v1.status_code == 200
    assert v1.json()["contract"] == "generic-parser-module-v1"


def test_v2_validation_normalizes_comma_terms_and_rejects_project_fields():
    client = TestClient(transport.app)
    body = request_body()
    validate = {
        "contract": body["contract"],
        "batch_id": body["batch_id"],
        "client": body["client"],
        "searches": [body["search"]],
    }
    response = client.post("/api/module/v2/validate", json=validate)
    assert response.status_code == 200
    assert response.json()["searches"][0]["criteria"]["required_terms"] == ["Märklin", "H0/AC"]

    validate["searches"][0]["market_value"] = 100
    rejected = client.post("/api/module/v2/validate", json=validate)
    assert rejected.status_code == 422

    validate["searches"][0].pop("market_value")
    validate["searches"][0]["location"] = {"postal_code": "10115"}
    unverified_location = client.post("/api/module/v2/validate", json=validate)
    assert unverified_location.status_code == 422

    validate["searches"][0]["location"] = {}
    validate["searches"].append({**validate["searches"][0]})
    duplicate = client.post("/api/module/v2/validate", json=validate)
    assert duplicate.status_code == 422


def test_v2_search_returns_source_independent_listing_without_seller(monkeypatch):
    monkeypatch.setattr(transport, "load_service", lambda: fake_service())
    response = TestClient(transport.app).post("/api/module/v2/search", json=request_body())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["continuation_token"] is None
    listing = payload["results"][0]["listings"][0]
    assert listing["listing_key"] == "ebay:v1|123|0"
    assert listing["pricing"] == {
        "item": 40.0,
        "shipping": 5.49,
        "total": 45.49,
        "total_known": True,
        "currency": "EUR",
    }
    assert listing["classification"]["decision"] == "accept"
    assert "seller" not in json.dumps(listing).casefold()


def test_signed_continuation_resumes_and_is_bound_to_unchanged_search(monkeypatch):
    pages: list[int] = []

    async def search_page(payload, _request):
        pages.append(payload.page)
        result = await fake_service(next_page=1 if payload.page == 0 else None).search_page(payload, _request)
        result["pagination"]["next_page"] = 1 if payload.page == 0 else None
        result["pagination"]["complete"] = payload.page != 0
        return result

    monkeypatch.setattr(
        transport,
        "load_service",
        lambda: SimpleNamespace(SearchRequest=SearchRequest, search_page=search_page),
    )
    client = TestClient(transport.app)
    body = request_body()
    first = client.post("/api/module/v2/search", json=body)
    assert first.status_code == 200
    token = first.json()["continuation_token"]
    assert token and token.startswith("v2.")

    resumed_body = {**body, "continuation_token": token}
    resumed = client.post("/api/module/v2/search", json=resumed_body)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "complete"
    assert resumed.json()["continuation_token"] is None
    assert pages == [0, 1]

    changed = {**resumed_body, "search": {**body["search"], "query": "Andere Suche"}}
    conflict = client.post("/api/module/v2/search", json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "CONTINUATION_CONFLICT"


def test_batch_continuation_walks_searches_and_sources_in_order(monkeypatch):
    calls: list[tuple[str, str, int]] = []

    async def search_page(payload, _request):
        calls.append((payload.query, payload.source, payload.page))
        return {
            "listings": [],
            "pagination": {
                "current_page": payload.page,
                "next_page": None,
                "complete": True,
                "source": payload.source,
            },
            "source_status": {
                payload.source: {"enabled": True, "status": "ok", "http_status": 200}
            },
        }

    monkeypatch.setattr(
        transport,
        "load_service",
        lambda: SimpleNamespace(SearchRequest=SearchRequest, search_page=search_page),
    )
    single = request_body()
    first = {**single["search"], "search_id": "first", "query": "Erste Suche", "sources": ["kleinanzeigen", "vinted"]}
    second = {**single["search"], "search_id": "second", "query": "Zweite Suche", "sources": ["ebay"]}
    batch = {
        "contract": MODULE_CONTRACT_V2,
        "batch_id": "ordered-batch",
        "client": single["client"],
        "searches": [first, second],
        "debug": {"enabled": False},
    }
    client = TestClient(transport.app)
    packets: list[dict] = []
    while True:
        response = client.post("/api/module/v2/batch", json=batch)
        assert response.status_code == 200
        packets.append(response.json())
        token = response.json()["continuation_token"]
        if not token:
            break
        batch = {**batch, "continuation_token": token}

    assert calls == [
        ("Erste Suche", "kleinanzeigen", 0),
        ("Erste Suche", "vinted", 0),
        ("Zweite Suche", "ebay", 0),
    ]
    assert [item["results"][0]["search_id"] for item in packets] == ["first", "first", "second"]
    assert packets[-1]["status"] == "complete"
    assert packets[-1]["progress"]["searches_complete"] == 2
    assert packets[-1]["progress"]["sources_complete"] == 3


def test_continuation_rejects_tampering_and_expiry():
    secret = b"unit-test-secret"
    token = encode_continuation({"batch_id": "b", "fingerprint": "f"}, secret=secret, now=10)
    assert decode_continuation(token, secret=secret, now=11)["batch_id"] == "b"
    body, signature = token.rsplit(".", 1)
    tampered = f"{body}.{signature[:-1]}{'A' if signature[-1] != 'A' else 'B'}"
    try:
        decode_continuation(tampered, secret=secret, now=11)
    except ValueError as exc:
        assert "invalid" in str(exc)
    else:  # pragma: no cover - cryptographic guard
        raise AssertionError("tampered continuation token was accepted")

    try:
        decode_continuation(token, secret=secret, now=10 + 2 * 60 * 60 + 1)
    except ContinuationExpired:
        pass
    else:  # pragma: no cover - expiry guard
        raise AssertionError("expired continuation token was accepted")


def test_all_failed_source_packet_is_explicit_and_retryable(monkeypatch):
    monkeypatch.setattr(
        transport,
        "load_service",
        lambda: fake_service(status="degraded", http_status=429),
    )
    response = TestClient(transport.app).post("/api/module/v2/search", json=request_body())
    assert response.status_code == 502
    assert response.json()["stop_reason"] == "all_sources_failed"
    status = response.json()["results"][0]["sources"]["ebay"]
    assert status["status"] == "rate_limited"
    assert status["retryable"] is True


def test_web_ui_160_uses_v2_and_exposes_clear_search_and_result_controls():
    html = read("cloudflare/public/index.html")
    app = read("cloudflare/public/app.js")
    ui = read("cloudflare/public/ui-160.js")
    service_worker = read("cloudflare/public/service-worker.js")
    for identifier in (
        "search-source",
        "required-terms",
        "excluded-terms",
        "source-progress",
        "active-result-filters",
        "filter-known-total",
        "filter-favorites",
        "mobile-filter-toggle",
    ):
        assert f'id="{identifier}"' in html
    assert "Passend &amp; Prüfen" in html
    assert "generic-parser-module-v2" in app
    assert "api/module/v2/search" in app
    assert "'search-source'" in app[app.index("const ids=") : app.index("function refreshProfiles")]
    assert "market_value" not in app[app.index("function v2Definition") : app.index("function v2Request")]
    assert "parseTermList" in ui
    assert "generic-parser-mobile-gp-162" in service_worker
    assert '"./ui-160.css"' in service_worker
    assert '"./ui-161.css"' in service_worker
    assert '"./ui-160.js"' in service_worker
    assert "service-worker.js?v=gp-162" in app
    controller = read("cloudflare/public/controller-0450.js")
    assert "requestPage = async function(payload, state)" in controller
    assert "originalRequestPage(payload, state)" in controller
    assert "requestPage(payload, s)" in controller


def test_openapi_document_and_release_docs_are_present():
    openapi = json.loads(read("docs/openapi-module-v2.json"))
    assert openapi["info"]["version"] == VERSION
    assert "/api/module/v2/batch" in openapi["paths"]
    assert "/api/module/v2/search" in openapi["paths"]
    assert "market_value" not in json.dumps(openapi)
    assert "generic-parser-module-v2" in read("docs/API_1.6.0.md")
    assert "module-v1" in read("docs/releases/1.6.0.md")
    assert "controller bridge" in read("docs/releases/1.6.1.md").casefold()
    assert "fail" in read("docs/releases/1.6.2.md").casefold()
    assert "service-worker" in read("docs/releases/1.6.2.md").casefold()
