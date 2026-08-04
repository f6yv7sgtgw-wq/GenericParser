from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_is_consistent():
    identity = text("src/generic_parser/build_identity_v04463.py")
    browser = text("cloudflare/public/build-identity-04463.js")
    assert 'VERSION = "0.44.6.3"' in identity
    assert 'BUILD_ID = "gp-04463-20260804-1"' in identity
    assert 'API_CONTRACT = "match-v6.11.4-reference-recovery-hardening"' in identity
    assert "version:'0.44.6.3'" in browser
    assert "buildId:'gp-04463-20260804-1'" in browser


def test_search_core_is_unchanged_reference_0444():
    source = text("src/generic_parser/search_service_v04463.py")
    assert "search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert 'REFERENCE_CORE_MODULE = "generic_parser.search_service_v0444"' in source
    assert "SEARCH_BEHAVIOR_CHANGED = False" in source
    assert "worker_runtime_v0445" not in source


def test_recovery_probe_loads_full_search_path_without_search_request():
    source = text("src/generic_parser/cloudflare_v04463.py")
    assert '@app.get("/api/recovery-probe")' in source
    assert "service = load_service()" in source
    assert '"request_model_ready"' in source
    assert '"search_callable"' in source
    assert '"reference_core"' in source
    probe_section = source.split('@app.get("/api/recovery-probe")', 1)[1].split('@app.post("/api/search")', 1)[0]
    assert "search_page(" not in probe_section
    assert "Kleinanzeigen" not in probe_section


def test_recovery_controller_uses_staged_backoff_and_two_resumes():
    identity = text("cloudflare/public/build-identity-04463.js")
    recovery = text("cloudflare/public/auto-resume-04463.js")
    assert "backoffMs:[90000,180000,360000]" in identity
    assert "probeIntervalsMs:[30000,60000,120000]" in identity
    assert "maxAutoResumes:2" in identity
    assert "jitterRatio:0.10" in identity
    assert "recovery_scheduled" in recovery
    assert "recovery_probe_ready" in recovery
    assert "recovery_resume_start" in recovery
    assert "recovery_manual_required" in recovery
    assert "button.click()" in recovery
    assert "options.maxAutoResumes" in recovery


def test_controller_keeps_reference_flow_and_adds_error_headers_only():
    source = text("cloudflare/public/controller-04463.js")
    assert "controller-0411.js" in source
    assert "cf-error-type" in source
    assert "cf-error-origin" in source
    assert "retry-after" in source
    assert "cursor_url" not in source
    assert "worker_runtime_v0445" not in source
    assert "searchCoreChanged:false" in source


def test_active_entrypoint_and_ui_use_04463():
    worker = text("src/generic_parser/cloudflare_worker.py")
    index = text("cloudflare/public/index.html")
    eventlog = text("cloudflare/public/eventlog.html")
    assert "from generic_parser.cloudflare_v04463 import app" in worker
    assert "build-identity-04463.js" in index
    assert "controller-04463.js" in index
    assert "auto-resume-04463.js" in index
    assert "eventlog-04463.js" in eventlog
    assert "0.44.6.3" in index and "0.44.6.3" in eventlog


def test_metadata_marks_04462_as_working_reference():
    metadata = text("VERSION.json")
    assert '"version": "0.44.6.3"' in metadata
    assert '"working_reference_version": "0.44.6.2"' in metadata
    assert '"max_auto_resumes_per_search_chain": 2' in metadata
    assert '"search_core_diff_allowed": false' in metadata
