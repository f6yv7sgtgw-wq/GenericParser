import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PUBLIC=ROOT/'cloudflare'/'public'

def test_cloudflare_configuration_is_mobile_worker_ready()->None:
    config=json.loads((ROOT/'wrangler.jsonc').read_text(encoding='utf-8'))
    assert config['main']=='src/generic_parser/cloudflare_worker.py'
    assert 'python_workers' in config['compatibility_flags']
    assert {'/api/*','/health','/version','/diagnostics','/search'}.issubset(set(config['assets']['run_worker_first']))

def test_pwa_manifest_and_required_assets_exist()->None:
    manifest=json.loads((PUBLIC/'manifest.webmanifest').read_text(encoding='utf-8'))
    assert manifest['display']=='standalone' and manifest['start_url']=='./' and manifest['scope']=='./'
    for path in ['index.html','app.css','app.js','service-worker.js','icons/icon.svg']: assert (PUBLIC/path).is_file(),path

def test_mobile_interface_uses_0452_build2_identity_with_unchanged_controller()->None:
    html=(PUBLIC/'index.html').read_text(encoding='utf-8'); js=(PUBLIC/'app.js').read_text(encoding='utf-8'); controller=(PUBLIC/'controller-0450.js').read_text(encoding='utf-8')
    assert 'GenericParser <span>0.45.2</span>' in html
    assert 'gp-0452-20260807-2' in html
    assert 'build-identity-0452.js' in html and 'controller-0450.js' in html
    assert 'Live-Suche starten' in controller
    assert 'const apiUrl=p=>new URL' in js and "apiUrl('api/search')" in js

def test_service_worker_cache_matches_build2_and_bypasses_api_paths()->None:
    worker=(PUBLIC/'service-worker.js').read_text(encoding='utf-8')
    assert 'generic-parser-mobile-0.45.2-gp-0452-20260807-2' in worker
    for asset in ['build-identity-0452.js','controller-0450.js','module-debug-0450.js','auto-resume-0450.js','eventlog-0450.js']: assert asset in worker
    for route in ['/health','/version','/diagnostics','/search']: assert route in worker
