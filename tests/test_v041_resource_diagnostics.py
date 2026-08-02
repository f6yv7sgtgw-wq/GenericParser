from __future__ import annotations

from pathlib import Path


def test_v041_worker_exposes_resource_fields() -> None:
    text = Path("src/generic_parser/cloudflare_v041.py").read_text(encoding="utf-8")
    for field in (
        "request_wall_ms",
        "process_cpu_ms",
        "html_fetch_ms",
        "html_parse_ms",
        "html_bytes",
        "mobile_total_ms",
        "mobile_response_bytes",
    ):
        assert field in text
    assert 'memory_note": "runtime_not_exposed"' in text
    assert "X-GenericParser-Resources" in text


def test_v041_production_entrypoint() -> None:
    text = Path("src/generic_parser/cloudflare_worker.py").read_text(encoding="utf-8")
    assert "cloudflare_v041 import app" in text
    assert "0.41.0" in text


def test_v041_frontend_and_cache_are_consistent() -> None:
    index = Path("cloudflare/public/index.html").read_text(encoding="utf-8")
    cache = Path("cloudflare/public/service-worker.js").read_text(encoding="utf-8")
    resource = Path("cloudflare/public/resource-041.js").read_text(encoding="utf-8")
    assert "GenericParser 0.41" in index
    assert "resource-041.js?v=0.410" in index
    assert 'generic-parser-mobile-0.41.0' in cache
    assert 'resource-041.js?v=0.410' in cache
    assert "X-GenericParser-Resources" in resource
