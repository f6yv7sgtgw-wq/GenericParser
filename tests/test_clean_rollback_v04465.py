from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_is_04465_and_points_to_04462_reference():
    identity = text("src/generic_parser/build_identity_v04465.py")
    browser = text("cloudflare/public/build-identity-04465.js")
    assert 'VERSION = "0.44.6.5"' in identity
    assert 'BUILD_ID = "gp-04465-20260804-1"' in identity
    assert 'API_CONTRACT = "match-v6.11.6-clean-rollback-04462"' in identity
    assert 'OPERATIONAL_REFERENCE = "0.44.6.2"' in identity
    assert "version:'0.44.6.5'" in browser
    assert "operationalReference:'0.44.6.2'" in browser
    assert "maxAutoResumes:1" in browser
    assert "quietPeriodMs:90000" in browser


def test_active_worker_is_the_confirmed_asgi_path_not_04464_lazy_bootstrap():
    source = text("src/generic_parser/cloudflare_worker.py")
    assert "import asgi" in source
    assert "from generic_parser.cloudflare_v04465 import app" in source
    assert "return await asgi.fetch(app, request, self.env)" in source
    assert "_load_asgi_app" not in source
    assert "direct-light-probe" not in source
    assert "build_identity_v04464" not in source
    assert 'path == "/api/recovery-probe"' not in source


def test_bootstrap_matches_single_resume_reference_behavior():
    source = text("src/generic_parser/cloudflare_v04465.py")
    assert '@app.get("/api/version")' in source
    assert '@app.post("/api/search")' in source
    assert '@app.get("/api/recovery-probe")' not in source
    assert '"mode": "single_saved-state-auto-resume"' in source
    assert '"quiet_period_ms": 90000' in source
    assert '"health_check_interval_ms": 15000' in source
    assert '"max_health_checks": 4' in source
    assert '"max_auto_resumes": 1' in source
    assert '"probe_endpoint": "/api/version"' in source
    assert '"experimental_04463_recovery": False' in source
    assert '"experimental_04464_lazy_bootstrap": False' in source


def test_search_service_delegates_unchanged_0444_core():
    source = text("src/generic_parser/search_service_v04465.py")
    assert "search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert '"search_behavior_changed": False' in source
    assert '"operational_reference": OPERATIONAL_REFERENCE' in source
    assert "worker_runtime_v0445" not in source
    assert "search_service_v04464" not in source


def test_browser_reuses_exact_04462_recovery_logic_with_new_storage_key():
    source = text("cloudflare/public/auto-resume-04465.js")
    assert "./auto-resume-04462.js" in source
    assert "generic-parser-auto-resume-04462" in source
    assert "generic-parser-auto-resume-04465" in source
    assert "recovery-probe" not in source
    assert "maxAutoResumes:2" not in source


def test_active_ui_uses_only_04465_assets():
    index = text("cloudflare/public/index.html")
    eventlog = text("cloudflare/public/eventlog.html")
    controller = text("cloudflare/public/controller-04465.js")
    assert "build-identity-04465.js" in index
    assert "controller-04465.js" in index
    assert "auto-resume-04465.js" in index
    assert "eventlog-04465.js" in eventlog
    assert "controller-0411.js" in controller
    assert "controller-04463.js" not in index
    assert "controller-04464.js" not in index
    assert "auto-resume-04463.js" not in index
    assert "auto-resume-04464.js" not in index


def test_metadata_marks_clean_rollback_and_disables_experiments():
    metadata = text("VERSION.json")
    assert '"version": "0.44.6.5"' in metadata
    assert '"operational_reference_version": "0.44.6.2"' in metadata
    assert '"rollback_reference_commit": "f55f31bcd878ec1edb0b8fc0ee9b5330c8ef0a0a"' in metadata
    assert '"max_auto_resumes_per_search_chain": 1' in metadata
    assert '"recovery_probe_endpoint_must_not_be_referenced": true' in metadata
    assert '"search_core_diff_allowed": false' in metadata
