from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_marks_build2_and_stable_reference() -> None:
    metadata = json.loads(read("VERSION.json"))
    assert metadata["version"] == "0.44.6.6"
    assert metadata["build_id"] == "gp-04466-20260804-2"
    assert metadata["test_release"] is True
    assert metadata["stable_reference_version"] == "0.44.6.5"
    assert metadata["runtime_reference_version"] == "0.44.6.2"
    change = metadata["single_behavior_change"]
    assert change["threshold_unique_results"] == 120
    assert change["repeat_every_unique_results"] == 120
    assert change["duration_ms"] == 90_000
    assert change["once_per_session"] is False
    assert change["mode"] == "replace_regular_delay"


def test_worker_uses_rollback_asgi_path_without_lazy_probe() -> None:
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


def test_controller_replaces_regular_delay_at_repeated_thresholds() -> None:
    controller = read("cloudflare/public/controller-04466.js")
    base = read("cloudflare/public/controller-0411.js")
    assert "./controller-0411.js?v=0.4466b2-reference-source" in controller
    assert "TEST_COOLDOWN_STEP = 120" in controller
    assert "TEST_COOLDOWN_MS = 90000" in controller
    assert "generic-parser-cooldown-04466-b2" in controller
    assert "state.nextThreshold" in controller
    assert "completedThresholds" in controller
    assert "while(Number(loaded||0)>=Number(state.nextThreshold" in controller
    assert "ms=TEST_COOLDOWN_MS" in controller
    assert "replace_regular_delay" in controller
    assert "repeated-multiples" in controller
    assert "cooldown_threshold_reached" in controller
    assert "cooldown_start" in controller
    assert "cooldown_resume" in controller
    assert "testCooldownDone = true" not in controller
    assert "  let requestSequence = 0;" in base
    assert "async function countdown(ms,page,loaded,label='Nächste Seite')" in base


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
    assert "mode:'replace_regular_delay'" in identity


def test_ui_loads_build2_active_assets() -> None:
    index = read("cloudflare/public/index.html")
    eventlog = read("cloudflare/public/eventlog.html")
    assert "gp-04466-20260804-2" in index
    assert "v=0.4466b2" in index
    assert "controller-04466.js" in index
    assert "auto-resume-04466.js" in index
    assert "120, 240, 360" in index
    assert "gp-04466-20260804-2" in eventlog
    assert "v=0.4466b2" in eventlog
    assert "eventlog-04466.js" in eventlog


def test_eventlog_exposes_repeated_cooldown_evidence() -> None:
    eventlog = read("cloudflare/public/eventlog-04466.js")
    assert "cooldown_threshold_reached" in eventlog
    assert "cooldown_start" in eventlog
    assert "cooldown_resume" in eventlog
    assert "cooldown_cancelled" in eventlog
    assert "repeat_every_unique_results" in eventlog
    assert "ausgeführte Testpausen" in eventlog
    assert "generic-parser-cooldown-04466-b2" in eventlog
