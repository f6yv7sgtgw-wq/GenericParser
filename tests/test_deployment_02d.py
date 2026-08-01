from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_workflow_is_safe_and_reproducible() -> None:
    text = (ROOT / ".github/workflows/cloudflare-deploy.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    assert workflow[True]["workflow_dispatch"] is None
    job = workflow["jobs"]["test-and-deploy"]
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


def test_deployment_check_targets_current_version() -> None:
    text = (ROOT / "scripts/check_deployment.py").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION = "0.2.0rc2"' in text
    assert '"/health"' in text
    assert '"/manifest.webmanifest"' in text
