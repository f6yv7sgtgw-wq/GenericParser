from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser.cloudflare_app import create_cloudflare_app
from generic_parser.sources.kleinanzeigen import FetchedPage

FIXTURES = Path(__file__).parent / "fixtures"


def page(name: str, url: str = "https://www.kleinanzeigen.de/s-test/k0") -> FetchedPage:
    return FetchedPage(url, url, 200, (FIXTURES / name).read_text(encoding="utf-8"))


def test_cloudflare_health() -> None:
    client = TestClient(create_cloudflare_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "0.2.0rc1"


def test_cloudflare_html_mode_parses_fixture() -> None:
    client = TestClient(create_cloudflare_app())
    response = client.post(
        "/api/search",
        json={
            "mode": "html",
            "query": "evercade",
            "html": page("kleinanzeigen_results.html").text,
            "max_results": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["listings"] == 1
    assert payload["summary"]["cards"] == 4
    assert payload["summary"]["duplicates"] == 1
    assert payload["summary"]["truncated"] is True


def test_cloudflare_live_mode_uses_single_fetch() -> None:
    calls: list[str] = []

    async def fetcher(url: str) -> FetchedPage:
        calls.append(url)
        return page("kleinanzeigen_results.html", url)

    client = TestClient(create_cloudflare_app(fetcher=fetcher))
    response = client.post("/api/search", json={"query": "zelda snes", "max_results": 20})
    assert response.status_code == 200
    assert len(calls) == 1
    assert response.json()["worker"]["single_page"] is True


def test_cloudflare_location_id_helper() -> None:
    client = TestClient(create_cloudflare_app())
    response = client.post(
        "/api/location-id",
        json={"url": "https://www.kleinanzeigen.de/s-37136/evercade/k0l1234r50"},
    )
    assert response.status_code == 200
    assert response.json() == {"location_id": 1234}


def test_cloudflare_rejects_incomplete_local_search() -> None:
    client = TestClient(create_cloudflare_app())
    response = client.post(
        "/api/search",
        json={"query": "evercade", "postal_code": "37136", "radius_km": 50},
    )
    assert response.status_code == 422


def test_cloudflare_reports_blocked_fixture() -> None:
    client = TestClient(create_cloudflare_app())
    response = client.post(
        "/api/search",
        json={
            "mode": "html",
            "query": "evercade",
            "html": page("kleinanzeigen_blocked.html").text,
        },
    )
    assert response.status_code == 429


def test_cloudflare_optional_token_protects_api() -> None:
    inner = create_cloudflare_app()

    class Env:
        APP_TOKEN = "secret"

    async def app(scope, receive, send):
        scope["env"] = Env()
        await inner(scope, receive, send)

    client = TestClient(app)
    denied = client.post(
        "/api/location-id",
        json={"url": "https://www.kleinanzeigen.de/s-test/k0l1234r50"},
    )
    assert denied.status_code == 401
    allowed = client.post(
        "/api/location-id",
        headers={"X-GenericParser-Token": "secret"},
        json={"url": "https://www.kleinanzeigen.de/s-test/k0l1234r50"},
    )
    assert allowed.status_code == 200
