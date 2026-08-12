from pathlib import Path


def test_build5_worker_edge_preflight_contract():
    source = Path('src/generic_parser/cloudflare_worker.py').read_text(encoding='utf-8')
    identity = Path('src/generic_parser/build_identity_v0452.py').read_text(encoding='utf-8')

    assert 'from .release_identity import' in identity
    assert 'str(request.method).upper()=="OPTIONS"' in source
    assert 'Access-Control-Allow-Origin' in source
    assert 'Access-Control-Allow-Methods' in source
    assert 'Access-Control-Allow-Headers' in source
    assert 'Access-Control-Request-Headers' in source
    assert 'X-Generic-Parser-Contract' in source
    assert 'X-Request-Id' in source
    assert 'Content-Type' in source
    assert 'status=204' in source
    assert 'worker-edge' in source


def test_build5_does_not_change_search_runtime():
    # The historical module name stays as an import path, but it must not carry
    # its own copies of the identity any more.
    from generic_parser import build_identity_v0452 as identity
    from generic_parser import release_identity

    assert identity.SEARCH_RUNTIME == release_identity.SEARCH_RUNTIME
    assert identity.SEARCH_MODULE == release_identity.SEARCH_MODULE
    assert identity.OPERATIONAL_REFERENCE == "0.44.6.5"
    assert identity.BUILD_ID == release_identity.BUILD_ID
