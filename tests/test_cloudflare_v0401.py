from generic_parser.cloudflare_v0401 import VERSION, app


def test_version() -> None:
    assert VERSION == "0.40.1"
    assert app is not None


def test_page_worker_keeps_single_page_contract() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/search" in paths
    assert "/health" in paths
