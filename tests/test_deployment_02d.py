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
    assert "--live-search" in text
    assert "steps.deploy.outputs.deployment_url" in text
    assert "Keine Cloudflare-Deployment-URL ermittelt" in text
    assert "cancel-in-progress: false" in text
    assert "Normalize and validate Cloudflare credentials" in text
    assert "tr -d '[:space:]'" in text
    assert 'echo "::add-mask::$normalized"' in text
    assert '>> "$GITHUB_ENV"' in text

    rollback_text = (ROOT / ".github/workflows/rollback-04465.yml").read_text(encoding="utf-8")
    rollback = yaml.safe_load(rollback_text)
    assert rollback[True] == {"workflow_dispatch": None}
    assert "push:" not in rollback_text


def test_deployment_files_exist() -> None:
    for path in [
        "docs/DEPLOYMENT.md",
        "docs/DEPLOYMENT_0_2D.md",
        "scripts/check_deployment.py",
        "scripts/check_release_metadata.py",
        "scripts/rollback-cloudflare.sh",
        ".github/workflows/cloudflare-deploy.yml",
        ".github/workflows/release-integrity.yml",
    ]:
        assert (ROOT / path).is_file(), path


def test_deployment_check_targets_current_version() -> None:
    text = (ROOT / "scripts/check_deployment.py").read_text(encoding="utf-8")
    assert 'ROOT / "VERSION.json"' in text
    assert '"/health"' in text
    assert '"/api/version"' in text
    assert '"/manifest.webmanifest"' in text
    assert '"/api/module/v1/profile/validate"' in text
    assert '"/api/module/v1/self-test?enabled=true"' in text
    assert '"/api/module/v1/search"' in text
    assert "len(listings) > 7" in text


def test_release_integrity_workflow_has_no_path_filter() -> None:
    text = (ROOT / ".github/workflows/release-integrity.yml").read_text(encoding="utf-8")
    assert "paths:" not in text
    assert "paths-ignore:" not in text
    assert "scripts/check_release_metadata.py" in text
    assert "scripts/run_release_tests.py" in text
