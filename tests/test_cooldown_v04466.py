from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_marks_044661_and_stable_reference() -> None:
    metadata = json.loads(read("VERSION.json"))
    assert metadata["version"] == "0.44.6.6.1"
    assert metadata["build_id"] == "gp-044661-20260805-1"
    assert metadata["test_release"] is True
    assert metadata["stable_reference_version"] == "0.44.6.5"
    assert metadata["runtime_reference_version"] == "0.44.6.2"
    changes = metadata["changes"]
    assert changes["cooldown_duration_ms"] == 120_000
    assert changes["recovery_quiet_period_ms"] == 120_000
    assert changes["resume_control_attempts"] == 2
    assert changes["resume_control_retry_ms"] == 10_000
    assert changes["search_core_changed"] is False


def test_worker_uses_reference_asgi_path_without_lazy_probe() -> None:
    worker = read("src/generic_parser/cloudflare_worker.py")
    assert "import asgi" in worker
    assert "from generic_parser.cloudflare_v04466 import app" in worker
    assert "urlparse" not in worker
    assert "recovery-probe" not in worker
    assert "lazy_asgi" not in worker


def test_search_service_delegates_unchanged_reference_core() -> None:
    service = read("src/generic_parser/search_service_v04466.py")
    assert "from . import search_service_v0444 as reference" in service
    assert "result = await reference.search_page(payload, request)" in service
    assert '"search_behavior_changed": False' in service
    assert '"cooldown_test_server_change": False' in service


def test_server_packet_behavior_is_unchanged_and_test_times_are_120_seconds() -> None:
    bootstrap = read("src/generic_parser/cloudflare_v04466.py")
    assert '"packet_size": 7' in bootstrap
    assert '"pause_ms": 5000' in bootstrap
    assert '"quiet_period_ms": 120000' in bootstrap
    assert '"max_auto_resumes": 1' in bootstrap
    assert '"resume_control_attempts": 2' in bootstrap
    assert '"resume_control_retry_ms": 10000' in bootstrap
    assert '"probe_endpoint": "/api/version"' in bootstrap
    assert '@app.get("/api/recovery-probe")' not in bootstrap
    assert '"repeat_every_unique_results": 120' in bootstrap
    assert '"duration_ms": 120000' in bootstrap
    assert '"worker_code_changed": False' in bootstrap


def test_controller_flow_matches_04465_and_contains_no_search_patch() -> None:
    controller = read("cloudflare/public/controller-04466.js")
    reference = read("cloudflare/public/controller-04465.js")
    assert "./controller-0411.js?v=0.44661-reference-source" in controller
    assert "Reference countdown anchor missing" not in controller
    assert "countdownAnchor" not in controller
    assert "TEST_COOLDOWN" not in controller
    assert controller.count("source = source.replace(from, to)") == 1
    assert reference.count("source = source.replace(from, to)") == 1
    assert "Function(`${source}" in controller
    assert "controllerFlowChanged:false" in controller
    assert "referenceController:'0.44.6.5'" in controller
    assert "recoveryControlFix:true" in controller


def test_cooldown_is_separate_fail_open_120_second_wrapper() -> None:
    cooldown = read("cloudflare/public/cooldown-04466.js")
    app = read("cloudflare/public/app.js")
    identity = read("cloudflare/public/build-identity-04466.js")
    assert "async function countdown(ms,page,loaded,label='Nächste Seite')" in app
    assert "const originalCountdown = window.countdown" in cooldown
    assert "typeof originalCountdown !== 'function'" in cooldown
    assert "window.GP_HANDSHAKE_READY" not in cooldown
    assert "window.countdown = async function cooldownAwareCountdown" in cooldown
    assert "if (label !== 'Nächste Seite')" in cooldown
    assert "return originalCountdown(ms, page, loaded, label)" in cooldown
    assert "I.testCooldown?.stateKey" in cooldown
    assert "Math.floor(count / STEP) * STEP" in cooldown
    assert "cooldown_threshold_reached" in cooldown
    assert "cooldown_start" in cooldown
    assert "cooldown_resume" in cooldown
    assert "durationMs:120000" in identity
    assert "stateKey:'generic-parser-cooldown-044661'" in identity


def test_recovery_force_enables_and_retries_resume_control() -> None:
    recovery = read("cloudflare/public/auto-resume-04466.js")
    identity = read("cloudflare/public/build-identity-04466.js")
    assert "./auto-resume-04462.js?v=0.44661-recovery-source" in recovery
    assert "generic-parser-auto-resume-044661" in recovery
    assert "button.classList.remove('hidden')" in recovery
    assert "button.disabled = false" in recovery
    assert "auto_resume_control_retry" in recovery
    assert "resume_control_failed_after_retry" in recovery
    assert "event.type === 'search_resume'" in recovery
    assert "quietPeriodMs:120000" in identity
    assert "controlRetryMs:10000" in identity
    assert "maxAutoResumes:1" in identity


def test_ui_load_order_preserves_reference_search() -> None:
    index = read("cloudflare/public/index.html")
    eventlog = read("cloudflare/public/eventlog.html")
    app_pos = index.index("app.js?v=0.44661")
    cooldown_pos = index.index("cooldown-04466.js?v=0.44661")
    controller_pos = index.index("controller-04466.js?v=0.44661")
    recovery_pos = index.index("auto-resume-04466.js?v=0.44661")
    assert app_pos < cooldown_pos < controller_pos < recovery_pos
    assert "gp-044661-20260805-1" in index
    assert "0.44.6.6.1" in index
    assert "gp-044661-20260805-1" in eventlog
    assert "v=0.44661" in eventlog


def test_eventlog_exposes_120_second_and_control_retry_evidence() -> None:
    eventlog = read("cloudflare/public/eventlog-04466.js")
    assert "120-Sekunden-Testpause gestartet" in eventlog
    assert "auto_resume_control_retry" in eventlog
    assert "resume_control_attempts" in eventlog
    assert "generic-parser-auto-resume-044661" in eventlog
