from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_edge_shell_has_dependency_free_diagnostics_and_preflight() -> None:
    worker = read('src/generic_parser/cloudflare_worker.py')
    assert 'VERSION = "0.45.2"' in worker
    assert 'BUILD_ID = "gp-0452-20260807-1"' in worker
    assert 'from workers import Response, WorkerEntrypoint' in worker
    assert 'if method == "OPTIONS"' in worker
    assert 'path == "/health"' in worker
    assert 'path in {"/version", "/api/version"}' in worker
    assert 'path == "/diagnostics"' in worker
    assert 'from generic_parser.cloudflare_v0451 import app' in worker
    assert worker.index('if method == "OPTIONS"') < worker.index('from generic_parser.cloudflare_v0451 import app')
    assert worker.index('path == "/health"') < worker.index('from generic_parser.cloudflare_v0451 import app')
    assert 'asgi_bootstrap_failed' in worker
    assert 'Access-Control-Allow-Origin' in worker
    assert 'X-GenericParser-Version' in worker


def test_0452_does_not_change_search_implementation() -> None:
    metadata = read('VERSION.json')
    worker = read('src/generic_parser/cloudflare_worker.py')
    assert 'generic_parser.search_service_v0450' in metadata
    assert 'generic-parser-module-v1' in metadata
    assert 'search_behavior_changed": false' not in metadata.lower() or 'search_core_diff_allowed": false' in metadata.lower()
    assert 'cloudflare_v0451 import app' in worker


def test_worker_first_routes_cover_browser_contract() -> None:
    config = read('wrangler.jsonc')
    for path in ['/api/*', '/health', '/version', '/diagnostics', '/search']:
        assert f'"{path}"' in config
