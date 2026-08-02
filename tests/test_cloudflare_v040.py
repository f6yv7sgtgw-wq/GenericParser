from generic_parser.cloudflare_v040 import VERSION, app


def test_version() -> None:
    assert VERSION == "0.40.0"


def test_runtime_route_exists() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/runtime" in paths
    assert "/api/search" in paths


def test_page_worker_contract_remains_single_page() -> None:
    from generic_parser.cloudflare_v039 import MOBILE_PAGE_SIZE, MAX_PAGE
    assert MOBILE_PAGE_SIZE == 41
    assert MAX_PAGE == 500
