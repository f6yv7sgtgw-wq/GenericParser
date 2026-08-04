from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]


def test_worker_entry_restores_reference_asgi_path():
    source = (ROOT / "src/generic_parser/cloudflare_worker.py").read_text(encoding="utf-8")
    assert "from generic_parser.cloudflare_v0446 import app" in source
    assert "return await asgi.fetch(app, request, self.env)" in source
    assert "worker_runtime_v0445" not in source
    assert "worker_runtime_v04451" not in source
    assert "worker_runtime_v04452" not in source


def test_0446_service_delegates_to_exact_0444_reference():
    source = (ROOT / "src/generic_parser/search_service_v0446.py").read_text(encoding="utf-8")
    assert "from . import search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert "worker_runtime_v0445" not in source


def test_controller_is_reference_identity_wrapper_only():
    source = (ROOT / "cloudflare/public/controller-0446.js").read_text(encoding="utf-8")
    assert "controller-0411.js" in source
    assert "referenceVersion:'0.44.4'" in source
    assert "cursor_url" not in source
    assert "coverage_diagnostics" not in source


def test_identity_is_consistent():
    namespace: dict[str, object] = {}
    identity_source = (ROOT / "src/generic_parser/build_identity_v0446.py").read_text(encoding="utf-8")
    exec(identity_source, namespace)
    assert namespace["VERSION"] == "0.44.6"
    assert namespace["BUILD_ID"] == "gp-0446-20260804-1"
    assert namespace["API_CONTRACT"] == "match-v6.11.1-reference-0444-rollback"
    assert namespace["FUNCTIONAL_REFERENCE"] == "0.44.4"


def test_wrapper_preserves_reference_result_and_only_updates_identity(monkeypatch):
    from generic_parser import search_service_v0446 as service

    reference_result = {
        "listings": [{"id": "1", "title": "SNES Spiel"}],
        "summary": {"fetched_listings": 1, "visible_listings": 1, "hidden_by_filter": 0},
        "pagination": {"unique_listings": 1, "next_page": 1},
        "worker": {"version": "0.44.4", "marker": "reference"},
        "deployment_identity": {"version": "0.44.4"},
    }

    async def fake_reference(payload, request):
        assert payload.query == "Snes"
        return reference_result

    monkeypatch.setattr(service.reference, "search_page", fake_reference)
    payload = SimpleNamespace(query="Snes")
    result = asyncio.run(service.search_page(payload, SimpleNamespace()))

    assert result["listings"] == [{"id": "1", "title": "SNES Spiel"}]
    assert result["pagination"]["next_page"] == 1
    assert result["worker"]["marker"] == "reference"
    assert result["worker"]["version"] == "0.44.6"
    assert result["worker"]["reference_version"] == "0.44.4"
    assert result["worker"]["experimental_0445_runtime"] is False
