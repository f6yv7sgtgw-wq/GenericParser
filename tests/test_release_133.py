import json
import re
import subprocess
from pathlib import Path

from generic_parser.release_identity import BUILD_ID, VERSION


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_133_identity_and_rollback_are_consistent() -> None:
    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert VERSION == "1.3.3"
    assert BUILD_ID == "gp-133-20260809-1"
    assert metadata["version"] == VERSION
    assert metadata["build_id"] == BUILD_ID
    assert metadata["status"] == "release-candidate"
    assert metadata["rollback_plan"] == {
        "last_stable_baseline": "1.3.2",
        "build_id": "gp-132-20260809-1",
    }
    assert metadata["sources"]["vinted"]["background_batch_size"] == 3
    assert metadata["sources"]["vinted"]["main_search_blocked"] is False
    assert public["version"] == VERSION
    assert public["build_id"] == BUILD_ID


def test_search_header_matches_shared_project_pattern() -> None:
    html = read("cloudflare/public/index.html")
    header_end = html.index("</header>")
    assert 'class="sticky-shell"' in html
    assert 'class="brand-mark"' in html
    assert 'class="version-badge"' in html
    assert "Log &amp; Diagnose" in html[:header_end]
    assert 'href="./eventlog.html"' in html[:header_end]
    assert "Kleinanzeigen &amp; Vinted durchsuchen" in html
    assert "Technische Details anzeigen" not in html
    assert "technical-toggle" not in html
    assert "technical-content" not in html
    # Runtime bookkeeping stays present for the proven 1.3.2 controller, but its
    # parent remains invisible and no user-facing toggle exposes it.
    assert 'id="summary"' in html
    assert 'id="diagnostics-card"' in html


def test_eventlog_uses_the_same_top_header() -> None:
    html = read("cloudflare/public/eventlog.html")
    header_end = html.index("</header>")
    assert 'data-page="eventlog"' in html
    assert 'class="brand-mark"' in html[:header_end]
    assert "Log &amp; Diagnose" in html[:header_end]
    assert 'href="./"' in html[:header_end]
    assert "Release-Identität und Quellenstatus" not in html


def test_vinted_cards_are_compact_expandable_and_responsive() -> None:
    html = read("cloudflare/public/index.html")
    app = read("cloudflare/public/app.js")
    css = read("cloudflare/public/ui-133.css")
    assert "ui-133.css" in html
    assert "function cleanDescription(value)" in app
    assert "description-toggle" in app
    assert "Mehr anzeigen" in app
    assert "Weniger anzeigen" in app
    assert "expandedDescriptions" in app
    assert "-webkit-line-clamp: 4" in css
    assert ".description-shell.is-expanded .description" in css
    assert "overflow-x: hidden" in css
    assert "@media (max-width: 520px)" in css
    assert ".listing { grid-template-columns: 1fr; }" in css


def test_hashtag_only_lines_are_removed_without_losing_prose() -> None:
    app = read("cloudflare/public/app.js")
    match = re.search(
        r"function cleanDescription\(value\)\{(?P<body>[\s\S]*?)\}\nfunction descriptionMarkup",
        app,
    )
    assert match, "cleanDescription function boundary missing"
    function_source = f"function cleanDescription(value){{{match.group('body')}}}"
    values = [
        "Komplett mit Hülle.\n#evercade #retro #gaming",
        "#evercade #retro\n#gaming #collection",
        "Text mit #evercade bleibt erhalten.",
        "Erste Zeile\n\n#nur #tags\nZweite Zeile",
        "Normaler Text #evercade #retro #gaming #sammlung",
    ]
    script = (
        function_source
        + "; const values = "
        + json.dumps(values)
        + "; process.stdout.write(JSON.stringify(values.map(cleanDescription)));"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == [
        "Komplett mit Hülle.",
        "",
        "Text mit #evercade bleibt erhalten.",
        "Erste Zeile\nZweite Zeile",
        "Normaler Text",
    ]


def test_runtime_identity_and_cache_use_the_new_ui_release() -> None:
    controller = read("cloudflare/public/controller-0450.js")
    eventlog = read("cloudflare/public/eventlog-0450.js")
    service_worker = read("cloudflare/public/service-worker.js")
    app = read("cloudflare/public/app.js")
    assert "querySelectorAll('[data-version]')" in controller
    assert "querySelectorAll('[data-version]')" in eventlog
    assert "Kleinanzeigen und Vinted sind verbunden." in controller
    assert "generic-parser-mobile-gp-133" in service_worker
    assert '"./ui-133.css"' in service_worker
    assert "service-worker.js?v=gp-133" in app
