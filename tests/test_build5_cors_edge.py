from pathlib import Path


def test_build5_worker_edge_preflight_contract():
    source = Path('src/generic_parser/cloudflare_worker.py').read_text(encoding='utf-8')
    identity = Path('src/generic_parser/build_identity_v0452.py').read_text(encoding='utf-8')

    assert 'gp-0452-20260807-5' in identity
    assert 'if str(request.method).upper() == "OPTIONS"' in source
    assert 'Access-Control-Allow-Origin' in source
    assert 'Access-Control-Allow-Methods' in source
    assert 'Access-Control-Allow-Headers' in source
    assert 'Access-Control-Request-Headers' in source
    assert 'X-Generic-Parser-Contract' in source
    assert 'X-Request-Id' in source
    assert 'Content-Type' in source
    assert 'status=204' in source
    assert 'worker-edge-build5' in source


def test_build5_does_not_change_search_runtime():
    identity = Path('src/generic_parser/build_identity_v0452.py').read_text(encoding='utf-8')
    assert 'SEARCH_RUNTIME = "0.45.0"' in identity
    assert 'SEARCH_MODULE = "generic_parser.search_service_v0450"' in identity
    assert 'OPERATIONAL_REFERENCE = "0.44.6.5"' in identity
