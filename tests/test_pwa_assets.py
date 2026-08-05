import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "cloudflare" / "public"


def test_cloudflare_configuration_is_mobile_worker_ready() -> None:
    config = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))
    assert config["main"] == "src/generic_parser/cloudflare_worker.py"
    assert "python_workers" in config["compatibility_flags"]
    assert config["assets"]["directory"] == "./cloudflare/public"
    assert "/api/*" in config["assets"]["run_worker_first"]


def test_pwa_manifest_and_required_assets_exist() -> None:
    manifest = json.loads((PUBLIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "./"
    assert manifest["scope"] == "./"
    for path in ["index.html", "app.css", "app.js", "service-worker.js", "icons/icon.svg"]:
        assert (PUBLIC / path).is_file(), path


def test_mobile_interface_supports_deployed_and_direct_file_modes() -> None:
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    js = (PUBLIC / "app.js").read_text(encoding="utf-8")
    controller = (PUBLIC / "controller-0450.js").read_text(encoding="utf-8")
    assert "Controller lädt" in html
    assert "Live-Suche starten" in controller
    assert "Demo anzeigen" in html
    assert "const apiUrl=p=>new URL" in js
    assert "apiUrl('api/search')" in js
    assert "register('./service-worker.js?v=0.450')" in js
    assert 'href="./app.css?v=0.450"' in html
    assert 'src="./app.js?v=0.450"' in html


def test_service_worker_cache_matches_active_release() -> None:
    worker = (PUBLIC / "service-worker.js").read_text(encoding="utf-8")
    assert 'generic-parser-mobile-0.45.0-gp-0450-20260805-1' in worker
    for asset in [
        "build-identity-0450.js",
        "controller-0450.js",
        "module-debug-0450.js",
        "auto-resume-0450.js",
        "eventlog-0450.js",
    ]:
        assert asset in worker
    assert "build-identity-0427.js" not in worker
