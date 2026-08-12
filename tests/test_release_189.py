from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "cloudflare" / "public"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_every_dynamically_fetched_browser_asset_exists():
    """Statisch nicht sichtbare fetch-Pfade fielen dem 1.6.5-Aufraeumen zum Opfer.

    auto-resume-04462.js wurde entfernt, weil keine Seite und kein Precache sie
    referenzierte - geladen wird sie aber ueber einen zusammengebauten String.
    """

    pattern = re.compile(r"""new URL\(\s*['"]\./([A-Za-z0-9._-]+\.js)""")
    missing: list[str] = []
    for script in sorted(PUBLIC.glob("*.js")):
        for name in pattern.findall(script.read_text(encoding="utf-8")):
            if not (PUBLIC / name).is_file():
                missing.append(f"{script.name} lädt {name}")
    assert missing == [], missing


def test_the_recovery_source_carries_the_key_the_loader_patches():
    loader = read("cloudflare/public/auto-resume-0450.js")
    source = read("cloudflare/public/auto-resume-04462.js")
    fragment = "const RECOVERY_KEY = 'generic-parser-auto-resume-04462';"
    assert fragment in loader, "Loader erwartet das Fragment"
    assert fragment in source, "Ohne das Fragment bricht der Loader ab"
    assert '"./auto-resume-04462.js",' in read("cloudflare/public/service-worker.js")


def test_a_run_is_logged_from_start_to_finish():
    app_js = read("cloudflare/public/app.js")
    for event in ("'search_started'", "'search_packet'", "'search_finished'"):
        assert event in app_js, event
    # Das Ende muss auch bei manueller Pause und bei Abbruch geschrieben werden.
    assert "finally{window.gpEventLog?.('search_finished'" in app_js
    assert "sources:s.sourceOutcomes||{}" in app_js


def test_the_reason_line_is_dropped_where_it_carries_nothing():
    app_js = read("cloudflare/public/app.js")
    assert "${traffic.color==='green'?'':`<details class=\"match-reason\"" in app_js


def test_version_metadata_records_the_new_guarantees():
    verification = json.loads(read("VERSION.json"))["verification"]
    assert verification["dynamic_asset_paths_resolve"] == "required"
    assert verification["run_logged_start_to_finish"] == "required"


def test_the_controller_runtime_source_carries_every_patched_pattern():
    """Fehlte die Quelle, brach der Loader ab - und mit ihm die Abschaltung der
    Drosselung, die genau in diesem .then() steht. Das war der Fuenf-Sekunden-
    Timer aus 1.8.6."""

    loader = read("cloudflare/public/controller-0450.js")
    source = read("cloudflare/public/controller-0411.js")
    for fragment in ("const VERSION = '", "const COOLDOWN_MS = ", "const raw = await dbGet();"):
        assert fragment in source, fragment
    assert "./controller-0411.js" in loader
    assert '"./controller-0411.js",' in read("cloudflare/public/service-worker.js")
