from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_browser_decides_about_throttling_itself():
    app_js = read("cloudflare/public/app.js")
    # Bis 1.8.5 hing die Abschaltung an einer Zuweisung aus controller-0450.js.
    # Die sitzt in einem .then() und unterbleibt bei einem Ladefehler stumm.
    assert "function protectionDelaysOn()" in app_js
    assert "i.protectionDelays===false||i.workerPlan==='paid'" in app_js
    assert "function adaptiveDelay(base,latency){if(!protectionDelaysOn())return base;" in app_js


def test_a_rotating_search_is_not_paused_between_packets():
    app_js = read("cloudflare/public/app.js")
    assert "function rotatesSources(s)" in app_js
    assert "s.nextDelay>0&&!rotatesSources(s))await countdown(" in app_js


def test_the_paid_profile_is_declared_without_protection_delays():
    identity = read("cloudflare/public/build-identity-0450.js")
    assert "workerPlan: 'paid'" in identity
    assert "protectionDelays: false" in identity


def test_version_metadata_records_the_throttle_contract():
    verification = json.loads(read("VERSION.json"))["verification"]
    assert verification["successful_packet_delay_ms"] == 0
    assert verification["browser_owns_throttle_decision"] == "required"
    assert verification["no_inter_packet_pause_while_rotating"] == "required"
