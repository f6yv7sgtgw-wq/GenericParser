from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser.cloudflare_v0452 import app
from generic_parser.release_identity import BUILD_ID, VERSION


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_metadata_and_rollback_are_consistent():
    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert VERSION == "1.4.0"
    assert BUILD_ID == "gp-140-20260809-1"
    assert metadata["version"] == public["version"] == VERSION
    assert metadata["build_id"] == public["build_id"] == BUILD_ID
    assert metadata["status"] in {"release-candidate", "stable"}
    assert metadata["rollback_plan"] == {
        "last_stable_baseline": "1.3.4",
        "build_id": "gp-134-20260809-1",
    }
    assert metadata["verification"]["ebay_production_access_gate"] == "passed"
    assert metadata["verification"]["ebay_production_access_workflow_run"] == 31336200661


def test_ebay_is_the_third_default_source_with_official_transport():
    metadata = json.loads(read("VERSION.json"))
    ebay = metadata["sources"]["ebay"]
    assert metadata["sources"]["default"] == ["kleinanzeigen", "vinted", "ebay"]
    assert ebay["strategy"] == "official Browse API"
    assert ebay["marketplace"] == "EBAY_DE"
    assert ebay["fixed_price_default"] is True
    assert ebay["auctions_enabled_by_default"] is False
    assert ebay["listing_persistence"] is False
    assert ebay["price_semantics"] == "item plus known shipping total"


def test_capabilities_publish_ebay_contract_without_changing_module_version():
    response = TestClient(app).get("/api/module/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contract"] == "generic-parser-module-v1"
    assert payload["sources"] == ["kleinanzeigen", "vinted", "ebay"]
    assert payload["default_sources"] == payload["sources"]
    assert payload["ebay"] == {
        "strategy": "official-browse-api",
        "marketplace": "EBAY_DE",
        "fixed_price_default": True,
        "auctions_optional": True,
        "auctions_enabled_by_default": False,
        "price_semantics": "total-including-known-shipping",
        "persistence": False,
    }


def test_worker_reads_ebay_secrets_request_scoped_without_hardcoding():
    worker = read("src/generic_parser/cloudflare_worker.py")
    adapter = read("src/generic_parser/ebay_adapter.py")
    example = read("cloudflare/.dev.vars.example")
    assert 'getattr(self.env,"EBAY_CLIENT_ID",None)' in worker
    assert 'getattr(self.env,"EBAY_CLIENT_SECRET",None)' in worker
    assert "set_ebay_credentials" in worker
    assert "reset_ebay_credentials" in worker
    assert "EBAY_CLIENT_ID=" in example
    assert "EBAY_CLIENT_SECRET=" in example
    assert "api.ebay.com/buy/browse/v1/item_summary/search" in adapter
    assert "api.sandbox.ebay.com" not in adapter


def test_browser_exposes_auction_switch_total_price_and_no_ebay_persistence():
    html = read("cloudflare/public/index.html")
    app_js = read("cloudflare/public/app.js")
    controller = read("cloudflare/public/controller-0450.js")
    service_worker = read("cloudflare/public/service-worker.js")
    assert 'id="include-ebay-auctions" type="checkbox"' in html
    assert "p.include_ebay_auctions=$('include-ebay-auctions').checked" in app_js
    assert "sourceOf(item)!=='ebay'" in app_js
    assert "fingerprints:[]" in app_js
    assert "history:[]" in app_js
    assert "fetched:items.length" in app_js
    assert "ebayPersistence:false" in controller
    assert "total_price" in app_js
    assert "Versandkosten offen" in app_js
    assert '"./source-colors-140.css"' in service_worker
    assert '"./source-colors-140.js"' in service_worker


def test_deployment_gate_requires_secrets_and_live_ebay_results():
    workflow = read(".github/workflows/cloudflare-deploy.yml")
    assert "EBAY_CLIENT_ID" in workflow
    assert "EBAY_CLIENT_SECRET" in workflow
    assert "official-browse-api" in workflow
    assert "ebay_listings" in workflow
    assert "total_price" in workflow


def test_roadmap_and_api_document_the_inserted_ebay_release():
    roadmap = read("ROADMAP.md")
    api = read("docs/API_1.4.0.md")
    release = read("docs/releases/1.4.0.md")
    assert "## 1.4 – eBay production integration" in roadmap
    assert "## 1.5 – Product classification" in roadmap
    assert "## 1.6 – Title and cartridge normalization" in roadmap
    assert "include_ebay_auctions" in api
    assert "item_price" in api and "shipping_cost" in api and "total_price" in api
    assert "No eBay listing persistence" in release
