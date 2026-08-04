from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_marks_test_release_and_stable_reference() -> None:
    metadata = json.loads(read("VERSION.json"))
    assert metadata["version"] == "0.44.6.6"
    assert metadata["build_id"] == "gp-04466-20260804-1"
    assert metadata["test_release"] is True
    assert metadata["stable_reference_version"] == "0.44.6.5"
    assert metadata["runtime_reference_version"] == "0.44.6.2"
    change = metadata["single_behavior_change"]
    assert change["threshold_unique_results"] == 120
    assert change["duration_ms"] == 90_000
    assert change["once_per_session"] is True
    assert change["mode"] == "client_request_gate"


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
    assert '"mode": "single_saved-state-auto-resume"' in bootstrap
    assert '"quiet_period_ms": 90000' in bootstrap
    assert '"max_auto_resumes": 1' in bootstrap
    assert '"probe_endpoint": "/api/version"' in bootstrap
    assert '@app.get("/api/recovery-probe")' not in bootstrap


def test_controller_patches_only_client_request_stream() -> None:
    controller = read("cloudflare/public/controller-04466.js")
    base = read("cloudflare/public/controller-0411.js")
    assert "./controller-0411.js?v=0.4466-reference-source" in controller
    assert "TEST_COOLDOWN_THRESHOLD" in controller
    assert "TEST_COOLDOWN_MS" in controller
    assert "cooldown_threshold_reached" in controller
    assert "cooldown_start" in controller
    assert "cooldown_resume" in controller
    assert "client_request_gate" in controller
    assert "testCooldownDone = true" in controller
    assert "while (!stopRequested)" in controller
    assert "  let requestSequence = 0;" in base
    assert "    log('before_fetch', 'Vor Netzwerkaufruf', {...common, payload});" in base
    assert "if (!contentType.includes('application/json')" in base


def test_recovery_is_still_exact_04462_source() -> None:
    recovery = read("cloudflare/public/auto-resume-04466.js")
    identity = read("cloudflare/public/build-identity-04466.js")
    assert "./auto-resume-04462.js" in recovery
    assert "generic-parser-auto-resume-04466" in recovery
    assert "maxAutoResumes:1" in identity
    assert "quietPeriodMs:90000" in identity
    assert "healthIntervalMs:15000" in identity
    assert "maxHealthChecks:4" in identity


def test_ui_loads_only_04466_active_assets() -> None:
    index = read("cloudflare/public/index.html")
    eventlog = read("cloudflare/public/eventlog.html")
    assert "build-identity-04466.js" in index
    assert "controller-04466.js" in index
    assert "auto-resume-04466.js" in index
    assert "controller-04465.js" not in index
    assert "auto-resume-04465.js" not in index
    assert "build-identity-04466.js" in eventlog
    assert "eventlog-04466.js" in eventlog


def test_eventlog_exposes_cooldown_evidence() -> None:
    eventlog = read("cloudflare/public/eventlog-04466.js")
    assert "cooldown_threshold_reached" in eventlog
    assert "cooldown_start" in eventlog
    assert "cooldown_resume" in eventlog
    assert "cooldown_cancelled" in eventlog
    assert "Testpause-Ereignisse" in eventlog
