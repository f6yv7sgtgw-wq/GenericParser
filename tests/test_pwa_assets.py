import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "cloudflare" / "public"


def test_cloudflare_configuration_is_mobile_worker_ready() -> None:
    config = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))
    assert config["main"] == "src/generic_parser/cloudflare_worker.py"
    assert (ROOT / config["main"]).is_file()
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


def test_mobile_interface_addresses_assets_and_api_relatively() -> None:
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    js = (PUBLIC / "app.js").read_text(encoding="utf-8")
    # Assets and endpoints are resolved against the current document, so the
    # interface keeps working under any deployment path without a rebuild.
    assert 'href="./app.css"' in html
    assert 'src="./app.js' in html
    assert "new URL(p.replace(/^\\//,''),location.href)" in js
    assert "apiUrl('api/module/v2/search')" in js
    assert "register('./service-worker.js" in js
