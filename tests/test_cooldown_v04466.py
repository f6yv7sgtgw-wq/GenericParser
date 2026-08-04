from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_marks_build3_and_stable_reference() -> None:
    metadata = json.loads(read("VERSION.json"))
    assert metadata["version"] == "0.44.6.6"
    assert metadata["build_id"] == "gp-04466-20260804-3"
    assert metadata["test_release"] is True
    assert metadata["stable_reference_version"] == "0.44.6.5"
    assert metadata["runtime_reference_version"] == "0.44.6.2"
    assert metadata["build3_fix"]["fail_open"] is True
    change = metadata["single_behavior_change"]
    assert change["threshold_unique_results"] == 120
    assert change["repeat_every_unique_results"] == 120
    assert change["duration_ms"] == 90_000
    assert change["once_per_session"] is False
    assert change["mode"] == "repeated-multiples-fail-open"
    assert change["persistent_state_key"] == "generic-parser-cooldown-04466-b3"


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


def test_server_packet_and_recovery_behavior_remain_unchanged() -> None:
    bootstrap = read("src/generic_parser/cloudflare_v04466.py")
    assert '"packet_size": 7' in bootstrap
    assert '"pause_ms": 5000' in bootstrap
    assert '"mode": "single-saved-state-auto-resume"' in bootstrap
    assert '"quiet_period_ms": 90000' in bootstrap
    assert '"max_auto_resumes": 1' in bootstrap
    assert '"probe_endpoint": "/api/version"' in bootstrap
    assert '@app.get("/api/recovery-probe")' not in bootstrap
    assert '"repeat_every_unique_results": 120' in bootstrap
    assert '"once_per_session": False' in bootstrap
    assert '"worker_code_changed": False' in bootstrap


def test_controller_flow_matches_04465_and_contains_no_cooldown_patch() -> None:
    controller = read("cloudflare/public/controller-04466.js")
    reference = read("cloudflare/public/controller-04465.js")
    assert "./controller-0411.js?v=0.4466b3-reference-source" in controller
    assert "Reference countdown anchor missing" not in controller
    assert "countdownAnchor" not in controller
    assert "TEST_COOLDOWN" not in controller
    assert controller.count("source = source.replace(from, to)") == 1
    assert reference.count("source = source.replace(from, to)") == 1
    assert "Function(`${source}" in controller
    assert "controllerFlowChanged:false" in controller
    assert "referenceController:'0.44.6.5'" in controller


def test_cooldown_is_separate_fail_open_wrapper_around_app_countdown() -> None:
    cooldown = read("cloudflare/public/cooldown-04466.js")
    app = read("cloudflare/public/app.js")
    assert "async function countdown(ms,page,loaded,label='Nächste Seite')" in app
    assert "const originalCountdown = window.countdown" in cooldown
    assert "typeof originalCountdown !== 'function'" in cooldown
    assert "return;" in cooldown
    assert "window.GP_HANDSHAKE_READY" not in cooldown
    assert "window.countdown = async function cooldownAwareCountdown" in cooldown
    assert "if (label !== 'Nächste Seite')" in cooldown
    assert "return originalCountdown(ms, page, loaded, label)" in cooldown
    assert "generic-parser-cooldown-04466-b3" in cooldown
    assert "Math.floor(count / STEP) * STEP" in cooldown
    assert "cooldown_threshold_reached" in cooldown
    assert "cooldown_start" in cooldown
    assert "cooldown_resume" in cooldown


def test_recovery_is_still_exact_04462_source() -> None:
    recovery = read("cloudflare/public/auto-resume-04466.js")
    identity = read("cloudflare/public/build-identity-04466.js")
    assert "./auto-resume-04462.js" in recovery
    assert "generic-parser-auto-resume-04466" in recovery
    assert "maxAutoResumes:1" in identity
    assert "quietPeriodMs:90000" in identity
    assert "healthIntervalMs:15000" in identity
    assert "maxHealthChecks:4" in identity
    assert "repeatEvery:120" in identity
    assert "oncePerSession:false" in identity
    assert "mode:'repeated-multiples-fail-open'" in identity
    assert "gp-04466-20260804-3" in identity


def test_ui_load_order_preserves_reference_search() -> None:
    index = read("cloudflare/public/index.html")
    eventlog = read("cloudflare/public/eventlog.html")
    app_pos = index.index("app.js?v=0.4466b3")
    cooldown_pos = index.index("cooldown-04466.js?v=0.4466b3")
    controller_pos = index.index("controller-04466.js?v=0.4466b3")
    assert app_pos < cooldown_pos < controller_pos
    assert "gp-04466-20260804-3" in index
    assert "fail-open" in index
    assert "gp-04466-20260804-3" in eventlog
    assert "v=0.4466b3" in eventlog
    assert "eventlog-04466.js" in eventlog


def test_eventlog_exposes_repeated_cooldown_evidence() -> None:
    eventlog = read("cloudflare/public/eventlog-04466.js")
    assert "cooldown_threshold_reached" in eventlog
    assert "cooldown_start" in eventlog
    assert "cooldown_resume" in eventlog
    assert "cooldown_cancelled" in eventlog
    assert "repeat_every_unique_results" in eventlog
    assert "ausgeführte Testpausen" in eventlog
