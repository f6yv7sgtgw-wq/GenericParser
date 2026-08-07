from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

def test_deployment_workflow_is_safe_and_reproducible()->None:
    text=(ROOT/'.github/workflows/cloudflare-deploy.yml').read_text(encoding='utf-8'); workflow=yaml.safe_load(text)
    assert workflow[True]['workflow_dispatch'] is None
    job=workflow['jobs']['test-and-deploy']; assert job['environment']=='production'
    for marker in ['Deploy GenericParser 0.45.2','CLOUDFLARE_API_TOKEN','pywrangler deploy','scripts/check_deployment.py','--live-search','--browser-origin','EVERCADE_ORIGIN','steps.deploy.outputs.deployment_url','Keine Cloudflare-Deployment-URL ermittelt','cancel-in-progress: false','Normalize and validate Cloudflare credentials','build-identity-0452.js']:
        assert marker in text
    assert "tr -d '[:space:]'" in text
    assert 'echo "::add-mask::$normalized"' in text
    rollback_text=(ROOT/'.github/workflows/rollback-04465.yml').read_text(encoding='utf-8'); rollback=yaml.safe_load(rollback_text)
    assert rollback[True]=={'workflow_dispatch':None}; assert 'push:' not in rollback_text

def test_deployment_files_exist()->None:
    for path in ['docs/DEPLOYMENT.md','docs/DEPLOYMENT_0_2D.md','scripts/check_deployment.py','scripts/check_release_metadata.py','scripts/rollback-cloudflare.sh','.github/workflows/cloudflare-deploy.yml','.github/workflows/release-integrity.yml']:
        assert (ROOT/path).is_file(),path

def test_deployment_check_targets_0452_edge_contract()->None:
    text=(ROOT/'scripts/check_deployment.py').read_text(encoding='utf-8')
    for marker in ['/health','/version','/diagnostics','/api/module/search','/api/search','/search','OPTIONS','access-control-allow-origin','edge_shell','--browser-origin','len(listings)>7']:
        assert marker in text

def test_release_integrity_workflow_has_no_path_filter()->None:
    text=(ROOT/'.github/workflows/release-integrity.yml').read_text(encoding='utf-8')
    assert 'paths:' not in text and 'paths-ignore:' not in text
    assert 'scripts/check_release_metadata.py' in text and 'scripts/run_release_tests.py' in text
    assert 'build_identity_v0452.py' in text
