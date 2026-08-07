from fastapi.testclient import TestClient

from generic_parser.cloudflare_v0451 import app


def test_health_version_diagnostics_and_cors_contract() -> None:
    with TestClient(app) as client:
        health = client.get('/health', headers={'Origin': 'https://example.test'})
        assert health.status_code == 200
        assert health.json()['version'] == '0.45.1'
        assert health.json()['module_contract'] == 'generic-parser-module-v1'
        assert health.headers['access-control-allow-origin'] == '*'
        assert health.headers['x-request-id']

        version = client.get('/version')
        assert version.status_code == 200
        assert version.json()['build_id'] == 'gp-0451-20260807-1'

        diagnostics = client.get('/diagnostics')
        assert diagnostics.status_code == 200
        assert diagnostics.json()['checks']['cors'] is True
        assert diagnostics.json()['checks']['search_behavior_changed'] is False

        preflight = client.options(
            '/api/module/search',
            headers={
                'Origin': 'https://f6yv7sgtgw-wq.github.io',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type,x-generic-parser-contract',
            },
        )
        assert preflight.status_code == 204
        assert 'POST' in preflight.headers['access-control-allow-methods']
        assert 'Content-Type' in preflight.headers['access-control-allow-headers']


def test_required_search_aliases_are_registered_without_changing_v1_contract() -> None:
    paths = app.openapi()['paths']
    for path in ['/search', '/api/search', '/api/module/search', '/api/module/v1/search']:
        assert path in paths
        assert 'post' in paths[path]
