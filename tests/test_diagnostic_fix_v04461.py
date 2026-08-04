from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_is_consistent():
    identity = text("src/generic_parser/build_identity_v04461.py")
    assert 'VERSION = "0.44.6.1"' in identity
    assert 'BUILD_ID = "gp-04461-20260804-1"' in identity
    assert 'API_CONTRACT = "match-v6.11.2-reference-diagnostics"' in identity


def test_search_core_delegates_to_reference_0444_only():
    source = text("src/generic_parser/search_service_v04461.py")
    assert "search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert "worker_runtime_v0445" not in source
    assert '"search_behavior_changed": False' in source


def test_bootstrap_marks_reference_schema_optional():
    source = text("src/generic_parser/cloudflare_v04461.py")
    assert '"diagnostic_mode": "reference_optional"' in source
    assert '"coverage_schema_required": False' in source
    assert '"coverage_schema": None' in source
    assert '"pagination_strategy": "source_html_weiter_link"' in source


def test_eventlog_does_not_require_experimental_diagnostics():
    source = text("cloudflare/public/eventlog-04461.js")
    assert "worker.version === I.version" in source
    assert "worker.build_id === I.buildId" in source
    assert "worker.api_contract === I.apiContract" in source
    assert "robust_title_fallback===true" not in source
    assert "diagnostic_alignment===true" not in source
    assert "reference_optional" in source
    assert "Temporärer Abruffehler (HTTP 503)" in source
    assert "generic-parser-eventlog-0446" in source


def test_controller_keeps_reference_flow():
    source = text("cloudflare/public/controller-04461.js")
    assert "controller-0411.js" in source
    assert "cursor_url" not in source
    assert "worker_runtime_v0445" not in source


def test_ui_uses_04461_assets():
    index = text("cloudflare/public/index.html")
    eventlog = text("cloudflare/public/eventlog.html")
    assert "build-identity-04461.js" in index
    assert "controller-04461.js" in index
    assert "eventlog-04461.js" in eventlog
    assert "0.44.6.1" in index and "0.44.6.1" in eventlog
