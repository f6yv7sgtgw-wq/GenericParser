from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path:str)->str: return (ROOT/path).read_text(encoding='utf-8')

def test_edge_shell_has_dependency_free_diagnostics_and_preflight()->None:
    worker=read('src/generic_parser/cloudflare_worker.py')
    assert 'VERSION = "0.45.2"' in worker
    assert 'BUILD_ID = "gp-0452-20260807-2"' in worker
    assert 'from workers import Response, WorkerEntrypoint' in worker
    assert 'if method=="OPTIONS"' in worker
    assert 'path=="/health"' in worker
    assert 'path in {"/version","/api/version"}' in worker
    assert 'path=="/diagnostics"' in worker
    assert 'from generic_parser.cloudflare_v0452 import app' in worker
    assert worker.index('if method=="OPTIONS"') < worker.index('from generic_parser.cloudflare_v0452 import app')
    assert 'asgi_bootstrap_failed' in worker
    assert 'Access-Control-Allow-Origin' in worker

def test_build2_reuses_live_proven_0450_asgi_search_runtime()->None:
    wrapper=read('src/generic_parser/cloudflare_v0452.py')
    metadata=read('VERSION.json')
    assert 'from .cloudflare_v0450 import app, legacy_search, module_search' in wrapper
    assert 'app.add_api_route("/search", legacy_search' in wrapper
    assert 'app.add_api_route("/api/module/search", module_search' in wrapper
    assert 'generic_parser.search_service_v0450' in metadata
    assert 'generic-parser-module-v1' in metadata
    assert '"search_core_diff_allowed": false' in metadata.lower()

def test_worker_first_routes_cover_browser_contract()->None:
    config=read('wrangler.jsonc')
    for path in ['/api/*','/health','/version','/diagnostics','/search']:
        assert f'"{path}"' in config
