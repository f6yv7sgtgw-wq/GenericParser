from __future__ import annotations

import json
from pathlib import Path

from generic_parser.release_identity import BUILD_ID, VERSION


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_and_rollback_target_are_consistent():
    metadata = json.loads(read("VERSION.json"))
    public = json.loads(read("cloudflare/public/release-identity.json"))
    assert VERSION == "1.5.1"
    assert BUILD_ID == "gp-151-20260810-1"
    assert metadata["version"] == public["version"] == VERSION
    assert metadata["build_id"] == public["build_id"] == BUILD_ID
    assert metadata["status"] == "stable"
    assert metadata["verification"]["production_acceptance"] == "passed"
    assert metadata["verification"]["production_commit"] == (
        "20721cc6335c00b6e1f9560c228f5604376f81b3"
    )
    assert metadata["verification"]["production_workflow_run"] == 31365503492
    assert metadata["verification"]["vinted_browser_workflow_run"] == 31365503492
    assert metadata["verification"]["accepted_at"] == "2026-08-10T07:22:53Z"
    assert metadata["rollback_plan"] == {
        "last_stable_baseline": "1.5.0",
        "build_id": "gp-150-20260810-1",
    }


def test_manual_stop_is_never_presented_as_complete():
    controller = read("cloudflare/public/controller-0411.js")
    stop_block = controller[
        controller.index("async function stopCurrent") : controller.index(
            "window.fetch = async function controlledFetch"
        )
    ]
    assert "Suche pausiert" in stop_block
    assert "wurde manuell gestoppt" in stop_block
    assert "Der Stand ist gespeichert und fortsetzbar" in stop_block
    assert "Suchlauf manuell gestoppt" in stop_block
    assert "complete:false" in stop_block
    assert "resumable:true" in stop_block
    assert "vollständig beendet" not in stop_block

    app = read("cloudflare/public/app.js")
    assert "else if(s.stopped){workerState('Suche pausiert'" in app


def test_eventlog_normalizes_existing_and_new_manual_stop_events():
    eventlog = read("cloudflare/public/eventlog-0450.js")
    assert "event?.type === 'search_stopped'" in eventlog
    assert "title:'Suchlauf manuell gestoppt'" in eventlog
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
    assert "Standard: Rot ausgeblendet" in html
    assert "repeat(12, minmax(0, 1fr))" in css
    assert ".filter-grid > label:nth-child(-n + 6)" in css
    assert ".filter-grid > label:nth-child(n + 7)" in css
    assert "@media (max-width: 1100px)" in css
    assert "@media (max-width: 720px)" in css
    assert "@media (max-width: 360px)" in css


def test_current_browser_assets_are_cache_busted():
    service_worker = read("cloudflare/public/service-worker.js")
    app = read("cloudflare/public/app.js")
    assert 'const CACHE="generic-parser-mobile-gp-151"' in service_worker
    assert '"./ui-151.css"' in service_worker
    assert "service-worker.js?v=gp-151" in app


def test_ebay_notification_component_tracks_patch_release():
    component = read("pocs/ebay-notifications/src/index.js")
    package = json.loads(read("pocs/ebay-notifications/package.json"))
    assert "version: '1.5.1'" in component
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
