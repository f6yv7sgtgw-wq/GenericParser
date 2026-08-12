from __future__ import annotations

import json
import re
from pathlib import Path

from generic_parser.release_identity import BUILD_ID, VERSION


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_and_rollback_target_are_consistent():
    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert metadata["version"] == public["version"] == VERSION
    assert metadata["build_id"] == public["build_id"] == BUILD_ID
    assert metadata["status"] in {"release-candidate", "stable"}
    assert metadata["verification"]["production_acceptance"] in {"pending", "passed"}
    rollback = metadata["rollback_plan"]
    # Das Rollback-Ziel wandert mit jeder abgenommenen Version weiter.
    # Festgeschrieben ist nur, dass es ein anderes, formal gültiges Release
    # benennt - ein Rollback auf sich selbst wäre keines.
    assert set(rollback) == {"last_stable_baseline", "build_id"}
    assert re.fullmatch(r"\d+\.\d+(?:\.\d+)?", rollback["last_stable_baseline"])
    assert re.fullmatch(r"gp-\w+-\d{8}-\d+", rollback["build_id"])
    assert rollback["last_stable_baseline"] != metadata["version"]


def test_manual_stop_is_never_presented_as_complete():
    """Ein manuell gestoppter Lauf gilt als pausiert und fortsetzbar.

    Geprüft wird der ausgelieferte Auslieferungsstand `app.js`. Bis 1.6.4 hing
    die erste Hälfte dieses Tests am Controller 0411, der seit Langem nicht
    mehr ausgeliefert wurde; die Zusicherung selbst ist unverändert.
    """

    app = read("cloudflare/public/app.js")
    marker = "else if(s.stopped){"
    assert marker in app
    stop_block = app[app.index(marker) : app.index("else if(", app.index(marker) + len(marker))]

    # Der Zustand wird als Pause dargestellt, nicht als Abschluss.
    assert "Suche pausiert" in stop_block
    assert "Fortsetzbarer Stand gespeichert" in stop_block
    assert "Ergebnisse gespeichert" in stop_block
    # Der Fortsetzen-Knopf wird sichtbar gemacht.
    assert "$('resume-button').classList.remove('hidden')" in stop_block
    # Keine Abschlussformulierung im Pausenzweig.
    for finished in ("vollständig beendet", "abgeschlossen", "Suche beendet"):
        assert finished not in stop_block

    # Der Lauf startet nicht als abgeschlossen und der Stopp ist ein
    # eigener Zustand neben `complete`.
    assert "complete:false" in app
    assert "stopped:false" in app


def test_eventlog_normalizes_existing_and_new_manual_stop_events():
    eventlog = read("cloudflare/public/eventlog-0450.js")
    assert "search_stopped" in eventlog
    assert "Suche pausiert" in eventlog
    assert "Der gespeicherte Stand kann fortgesetzt werden." in eventlog


def test_filter_layout_is_balanced_and_responsive_without_changing_filters():
    html = read("cloudflare/public/index.html")
    css = read("cloudflare/public/ui-151.css")
    for identifier in (
        "filter-traffic",
        "filter-source",
        "filter-product-class",
        "filter-condition",
        "filter-price-min",
        "filter-price-max",
        "filter-shipping",
        "filter-scope",
        "filter-format",
    ):
        assert f'id="{identifier}"' in html
    assert html.index("ui-150.css") < html.index("ui-151.css")
    assert '<option value="without-red" selected>Passend &amp; Prüfen</option>' in html
    assert "repeat(12, minmax(0, 1fr))" in css
    assert ".filter-grid > label:nth-child(-n + 6)" in css
    assert ".filter-grid > label:nth-child(n + 7)" in css
    assert "@media (max-width: 1100px)" in css
    assert "@media (max-width: 720px)" in css
    assert "@media (max-width: 360px)" in css


def test_current_browser_assets_are_cache_busted():
    asset_tag = "-".join(BUILD_ID.split("-")[:2])
    service_worker = read("cloudflare/public/service-worker.js")
    app = read("cloudflare/public/app.js")
    assert f"generic-parser-mobile-{asset_tag}" in service_worker
    assert '"./ui-151.css"' in service_worker
    assert '"./ui-160.css"' in service_worker
    assert '"./ui-161.css"' in service_worker
    assert f"service-worker.js?v={asset_tag}" in app


def test_ebay_notification_component_tracks_patch_release():
    component = read("pocs/ebay-notifications/src/index.js")
    package = json.loads(read("pocs/ebay-notifications/package.json"))
    assert f"version: '{VERSION}'" in component
    assert package["version"] == VERSION


def test_deploy_gate_waits_for_notification_worker_propagation():
    workflow = read(".github/workflows/cloudflare-deploy.yml")
    gate = workflow[
        workflow.index("- name: Verify eBay endpoint health") : workflow.index(
            "- name: Deploy Python Worker"
        )
    ]
    assert "for attempt in $(seq 1 24)" in gate
    assert "d.get('version')==os.environ['EXPECTED_VERSION']" in gate
    assert "for attempt in $(seq 1 12)" in gate
    assert "sleep 10" in gate
    assert "sleep 5" in gate
    assert "d.get('challengeResponse')==expected" in gate


def test_release_documentation_covers_scope_and_non_changes():
    api = read("docs/API_1.5.1.md")
    release = read("docs/releases/1.5.1.md")
    assert "generic-parser-module-v1" in api
    assert "user_stopped" in api
    assert "search core" in release.lower()
    assert "Kleinanzeigen, Vinted and eBay" in release
