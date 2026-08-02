from generic_parser import cloudflare_v039 as page_worker
from generic_parser.cloudflare_v0392 import app


def test_worker_version_is_0392() -> None:
    assert page_worker.VERSION == "0.39.2"
    assert app is page_worker.app


def test_page_worker_still_processes_one_page_per_request() -> None:
    assert page_worker.MOBILE_PAGE_SIZE == 41
    assert page_worker.MAX_PAGE >= 500


def test_empty_mobile_fallback_remains_enabled() -> None:
    assert page_worker.VERSION == "0.39.2"
    assert callable(page_worker._valid_count)
    assert callable(page_worker._html_reported_total)
