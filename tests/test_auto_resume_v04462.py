from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_is_consistent():
    identity = text("src/generic_parser/build_identity_v04462.py")
    assert 'VERSION = "0.44.6.2"' in identity
    assert 'BUILD_ID = "gp-04462-20260804-1"' in identity
    assert 'API_CONTRACT = "match-v6.11.3-reference-auto-resume"' in identity


def test_search_core_is_still_exact_reference_wrapper():
    source = text("src/generic_parser/search_service_v04462.py")
    assert "search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert "worker_runtime_v0445" not in source
    assert '"search_behavior_changed": False' in source


def test_server_only_advertises_controller_recovery():
    source = text("src/generic_parser/cloudflare_v04462.py")
    assert '"mode": "single_saved-state_auto_resume"' not in source
    assert '"mode": "single-saved-state-auto-resume"' in source
    assert '"quiet_period_ms": 90000' in source
    assert '"health_check_interval_ms": 15000' in source
    assert '"max_health_checks": 4' in source
    assert '"max_auto_resumes": 1' in source
    assert '"search_core_changed": False' in source
    assert '"pagination_strategy": "source_html_weiter_link"' in source


def test_controller_keeps_reference_flow_and_loads_separate_recovery():
    controller = text("cloudflare/public/controller-04462.js")
    index = text("cloudflare/public/index.html")
    assert "controller-0411.js" in controller
    assert "cursor_url" not in controller
    assert "worker_runtime_v0445" not in controller
    assert "searchCoreChanged:false" in controller
    assert "auto-resume-04462.js" in index


def test_auto_resume_is_single_bounded_saved_state_recovery():
    source = text("cloudflare/public/auto-resume-04462.js")
    assert "quietPeriodMs || 90000" in source
    assert "healthIntervalMs || 15000" in source
    assert "maxHealthChecks || 4" in source
    assert "maxAutoResumes || 1" in source
    assert "event.reason === 'retry_exhausted'" in source
    assert "event.type === 'worker_1101'" in source
    assert "html503Requests.size >= 2" in source
    assert "new URL('./api/version', location.href)" in source
    assert "worker.version === I.version" in source
    assert "worker.build_id === I.buildId" in source
    assert "worker.api_contract === I.apiContract" in source
    assert "document.getElementById('resume-button')" in source
    assert "button.click()" in source
    assert "auto_resume_limit_reached" in source
    assert "manual_override" in source
    assert "#clear-progress" in source


def test_eventlog_exposes_recovery_sequence():
    source = text("cloudflare/public/eventlog-04462.js")
    for event_type in (
        "auto_resume_scheduled",
        "auto_resume_health_failed",
        "auto_resume_start",
        "auto_resume_running",
        "auto_resume_completed",
        "auto_resume_manual_required",
    ):
        assert event_type in source
    assert "generic-parser-eventlog-04461" in source
    assert "generic-parser-eventlog-0446" in source


def test_ui_and_metadata_use_04462_assets():
    index = text("cloudflare/public/index.html")
    eventlog = text("cloudflare/public/eventlog.html")
    version = text("VERSION.json")
    assert "build-identity-04462.js" in index
    assert "controller-04462.js" in index
    assert "auto-resume-04462.js" in index
    assert "eventlog-04462.js" in eventlog
    assert "0.44.6.2" in index and "0.44.6.2" in eventlog
    assert '"max_auto_resumes_per_search_chain": 1' in version
    assert '"search_core_diff_allowed": false' in version
