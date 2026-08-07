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


def test_mobile_interface_uses_0451_identity_with_unchanged_0450_controller() -> None:
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    js = (PUBLIC / "app.js").read_text(encoding="utf-8")
    controller = (PUBLIC / "controller-0450.js").read_text(encoding="utf-8")
    assert "GenericParser <span>0.45.1</span>" in html
    assert "gp-0451-20260807-1" in html
    assert "build-identity-0451.js" in html
    assert "controller-0450.js" in html
    assert "Live-Suche starten" in controller
    assert "const apiUrl=p=>new URL" in js
    assert "apiUrl('api/search')" in js


def test_service_worker_cache_matches_active_release() -> None:
    worker = (PUBLIC / "service-worker.js").read_text(encoding="utf-8")
    assert 'generic-parser-mobile-0.45.1-gp-0451-20260807-1' in worker
    for asset in [
        "build-identity-0451.js",
        "controller-0450.js",
        "module-debug-0450.js",
        "auto-resume-0450.js",
        "eventlog-0450.js",
    ]:
        assert asset in worker
    assert "build-identity-0427.js" not in worker
