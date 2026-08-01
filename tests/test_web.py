from pathlib import Path

from fastapi.testclient import TestClient

from generic_parser.web import create_app


def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(fixture_store_dir=tmp_path / "fixtures"))


def test_index_and_health(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        page = web.get("/")
        assert page.status_code == 200
        assert "GenericParser" in page.text
        assert "Testsuche" in page.text
        assert web.get("/health").json() == {"status": "ok", "version": "0.2.0b1"}


def test_fixture_catalog(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        payload = web.get("/api/fixtures").json()
    assert "kleinanzeigen_results.html" in payload["fixtures"]
    assert "kleinanzeigen_blocked.html" in payload["fixtures"]


def test_result_fixture_returns_diagnostics_and_listings(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        response = web.post(
            "/api/search",
            json={
                "mode": "fixture",
                "query": "evercade",
                "fixture_name": "kleinanzeigen_results.html",
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {
        "listings": 2,
        "cards": 4,
        "duplicates": 1,
        "card_errors": 1,
    }
    assert [item["id"] for item in payload["listings"]] == ["10001", "10002"]
    assert payload["diagnostics"][0]["state"] == "results"


def test_no_results_fixture_is_not_layout_error(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        response = web.post(
            "/api/search",
            json={
                "mode": "fixture",
                "query": "does-not-exist",
                "fixture_name": "kleinanzeigen_no_results.html",
            },
        )
    assert response.status_code == 200
    assert response.json()["diagnostics"][0]["state"] == "no_results"
    assert response.json()["listings"] == []


def test_layout_and_block_fixtures_return_clear_status(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        layout = web.post(
            "/api/search",
            json={
                "mode": "fixture",
                "query": "test",
                "fixture_name": "kleinanzeigen_layout_changed.html",
            },
        )
        blocked = web.post(
            "/api/search",
            json={
                "mode": "fixture",
                "query": "test",
                "fixture_name": "kleinanzeigen_blocked.html",
            },
        )
    assert layout.status_code == 422
    assert "Ergebniskarten" in layout.json()["detail"]
    assert blocked.status_code == 429
    assert "Geblockte" in blocked.json()["detail"]


def test_inline_html_mode(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent
    html = (root / "fixtures/kleinanzeigen_results.html").read_text(encoding="utf-8")
    with client(tmp_path) as web:
        response = web.post(
            "/api/search",
            json={"mode": "html", "query": "inline", "html": html},
        )
    assert response.status_code == 200
    assert response.json()["summary"]["listings"] == 2


def test_location_id_helper(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        response = web.post(
            "/api/location-id",
            json={"url": "https://www.kleinanzeigen.de/s-37136/test/k0l123456r50"},
        )
        missing = web.post(
            "/api/location-id",
            json={"url": "https://www.kleinanzeigen.de/s-test/k0"},
        )
    assert response.json() == {"location_id": 123456}
    assert missing.status_code == 422


def test_local_live_request_requires_postal_code_and_location_id(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        response = web.post(
            "/api/search",
            json={
                "mode": "live",
                "query": "evercade",
                "postal_code": "37136",
                "radius_km": 50,
            },
        )
    assert response.status_code == 422
    assert "Location-ID" in str(response.json())


def test_fixture_name_cannot_escape_package_directory(tmp_path: Path) -> None:
    with client(tmp_path) as web:
        response = web.post(
            "/api/search",
            json={
                "mode": "fixture",
                "query": "test",
                "fixture_name": "../../README.md",
            },
        )
    assert response.status_code == 404
