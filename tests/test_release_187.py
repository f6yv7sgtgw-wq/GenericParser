from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_browser_records_why_each_source_stopped():
    app_js = read("cloudflare/public/app.js")
    assert "function recordSourceOutcome(s,data)" in app_js
    assert "recordSourceOutcome(s,data);" in app_js
    # Ohne Grund bliebe nur, dass eine Quelle aufgehoert hat - nicht warum.
    assert "'source_finished'" in app_js
    assert "function sourceOutcomeMarkup(s)" in app_js
    assert "sourceOutcomeMarkup(s)+s.history" in app_js


def test_the_known_source_verdicts_are_named_in_plain_words():
    app_js = read("cloudflare/public/app.js")
    for status in ("blocked", "rate_limited", "timeout", "unavailable", "empty", "partial"):
        assert f"{status}:" in app_js, status


def test_version_metadata_requires_the_stop_reason():
    verification = json.loads(read("VERSION.json"))["verification"]
    assert verification["source_stop_reason_recorded"] == "required"
    assert verification["source_stop_reason_visible"] == "required"


def test_the_log_can_be_downloaded_as_a_file():
    html = read("cloudflare/public/eventlog.html")
    export = read("cloudflare/public/eventlog-187.js")
    worker = read("cloudflare/public/service-worker.js")
    assert 'id="download-log"' in html
    assert "./eventlog-187.js" in html
    # Ohne Precache liefert der Service Worker die neue Datei nicht mit aus.
    assert '"./eventlog-187.js",' in worker
    # Ein spaeter gelesenes Log muss einem Stand zuzuordnen sein.
    assert "build_id: identity.buildId" in export
    assert "exported_at: now" in export
    assert "URL.revokeObjectURL" in export
