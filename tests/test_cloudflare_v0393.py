from __future__ import annotations

from pathlib import Path

from generic_parser import cloudflare_v039 as page_worker
import generic_parser.cloudflare_v0393 as release


def test_release_uses_one_page_worker_contract() -> None:
    assert release.app is page_worker.app
    assert page_worker.VERSION == "0.39.3"


def test_frontend_contains_adaptive_resource_controls() -> None:
    app_js = Path("cloudflare/public/app.js").read_text(encoding="utf-8")
    assert "adaptiveDelay" in app_js
    assert "resourceTrend" in app_js
    assert "requestWithBackoff" in app_js
    assert "pauseWithStatus" in app_js
    assert "Worker wartet" in app_js
    assert "Ressourcentrend" in app_js


def test_frontend_contains_consistency_checks() -> None:
    app_js = Path("cloudflare/public/app.js").read_text(encoding="utf-8")
    assert "validatePage" in app_js
    assert "consistencyOf" in app_js
    assert "fetched !== visible + hidden" in app_js
    assert "Kumulative Dateninkonsistenz" in app_js
    assert "Daten konsistent" in app_js


def test_frontend_bounds_initial_dom_rendering() -> None:
    app_js = Path("cloudflare/public/app.js").read_text(encoding="utf-8")
    index_html = Path("cloudflare/public/index.html").read_text(encoding="utf-8")
    assert "renderLimit:80" in app_js
    assert "state.renderLimit += 80" in app_js
    assert 'id="show-more"' in index_html


def test_versions_are_consistent() -> None:
    index_html = Path("cloudflare/public/index.html").read_text(encoding="utf-8")
    app_js = Path("cloudflare/public/app.js").read_text(encoding="utf-8")
    service_worker = Path("cloudflare/public/service-worker.js").read_text(encoding="utf-8")
    worker_entry = Path("src/generic_parser/cloudflare_worker.py").read_text(encoding="utf-8")
    assert "0.39.3" in index_html
    assert "v=0.393" in index_html
    assert "v=0.393" in app_js
    assert "generic-parser-mobile-0.39.3" in service_worker
    assert "cloudflare_v0393" in worker_entry
