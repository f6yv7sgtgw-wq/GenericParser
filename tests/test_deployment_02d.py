import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_workflow_is_safe_and_reproducible() -> None:
    text = (ROOT / ".github/workflows/cloudflare-deploy.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    assert workflow[True]["workflow_dispatch"] is None
    job = workflow["jobs"]["test-deploy-live"]
    assert job["environment"] == "production"
    assert "CLOUDFLARE_API_TOKEN" in text
    assert "pywrangler deploy" in text
    assert "scripts/check_deployment.py" in text
    assert "cancel-in-progress: false" in text


def test_deployment_files_exist() -> None:
    for path in [
        "docs/DEPLOYMENT_0_2D.md",
        "scripts/check_deployment.py",
        "scripts/rollback-cloudflare.sh",
        ".github/workflows/cloudflare-deploy.yml",
    ]:
        assert (ROOT / path).is_file(), path


def test_deployment_check_derives_the_expected_release_identity() -> None:
    import importlib.util

    text = (ROOT / "scripts/check_deployment.py").read_text(encoding="utf-8")
    assert '"/health"' in text
    assert '"/version"' in text

    # A hard coded expectation would silently go stale with every release.
    metadata = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("check_deployment", ROOT / "scripts/check_deployment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.EXPECTED_VERSION == metadata["version"]
    assert module.EXPECTED_BUILD == metadata["build_id"]
    assert module.EXPECTED_CONTRACT == metadata["api_contract"]
