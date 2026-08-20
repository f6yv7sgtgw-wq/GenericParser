"""2.0.1: Aufgelöste Konvolute dürfen das Legacy-Paket nicht inkonsistent machen.

Der Legacy-Vertrag `/api/search` prüft jedes Paket auf
`fetched == visible + hidden`, `visible == len(listings)` und
`fetched == unique_listings`. Die Konvolut-Auflösung (seit 1.8.0) ersetzt eine
Konvolutkachel durch mehrere Einzelkacheln, ließ `fetched_listings` aber auf dem
Stand vor der Auflösung — jede Ergebnisseite mit einem auflösbaren Konvolut
wurde damit als "Arbeitspaket ist inkonsistent." (HTTP 500) abgewiesen. Die
SNES-Collect-Suche brach deshalb nach drei Versuchen ab.
"""

from __future__ import annotations

import asyncio

from generic_parser import search_service_v0450 as service


BUNDLE_DETAIL_HTML = (
    '<div id="viewad-description-text">'
    "Verkaufe meine SNES Sammlung:\n"
    "Super Mario World 25 €\n"
    "F-Zero 15 €\n"
    "Versand 5 €"
    "</div>"
)


def _ka_page() -> dict:
    single = {
        "id": "ka-1",
        "title": "90 Minutes European Prime Goal SNES",
        "url": "https://www.kleinanzeigen.de/s-anzeige/example/1",
        "price": 20,
        "result_info": {"offer_type": "Produkt", "condition": "gebraucht", "scope": "Einzelangebot"},
        "match": {"score": 100, "decision": "accept", "listing_class": "Passender Treffer", "reason": "ok"},
        "traffic_light": {"color": "green"},
    }
    bundle = {
        "id": "ka-2",
        "title": "SNES Konvolut Spielesammlung",
        "url": "https://www.kleinanzeigen.de/s-anzeige/example/2",
        "price": 40,
        "result_info": {"offer_type": "Produkt", "condition": "gebraucht", "scope": "Konvolut"},
        "match": {"score": 80, "decision": "review", "listing_class": "Konvolut", "reason": "Konvolut"},
        "traffic_light": {"color": "yellow"},
    }
    return {
        "listings": [single, bundle],
        "pagination": {"current_page": 0, "next_page": None, "complete": True, "source": "html-fallback", "unique_listings": 2},
        "summary": {"fetched_listings": 2, "visible_listings": 2, "hidden_by_filter": 0, "reported_total": 2},
        "traffic_light_summary": {"green": 1, "yellow": 1, "red": 0},
        "generated_urls": [],
        "worker": {},
    }


def _search(monkeypatch) -> dict:
    async def fake_ka(payload, request):
        return _ka_page()

    async def fake_detail(url: str) -> str:
        return BUNDLE_DETAIL_HTML

    monkeypatch.setattr(service.reference, "search_page", fake_ka)
    monkeypatch.setattr(service, "_fetch_detail_html", fake_detail)
    payload = service.SearchRequest.model_validate(
        {
            "mode": "live",
            "query": "snes spiele",
            "page": 0,
            "source": "kleinanzeigen",
            "accept_bundles": True,
            "include_review": True,
            "include_rejected": True,
        }
    )
    return asyncio.run(service.search_page(payload, None))


def test_bundle_expansion_actually_derives_single_tiles(monkeypatch):
    result = _search(monkeypatch)
    derived = [item for item in result["listings"] if item.get("derived")]
    assert len(derived) == 2
    assert result["bundle_resolution"]["resolved"] == 1
    assert all(item["url"] == "https://www.kleinanzeigen.de/s-anzeige/example/2" for item in derived)


def test_expanded_packet_satisfies_the_legacy_consistency_contract(monkeypatch):
    result = _search(monkeypatch)
    summary = result["summary"]
    pagination = result["pagination"]
    fetched = int(summary["fetched_listings"])
    visible = int(summary["visible_listings"])
    hidden = int(summary["hidden_by_filter"])
    assert fetched == visible + hidden
    assert visible == len(result["listings"])
    assert fetched == int(pagination["unique_listings"])


def test_unexpanded_packet_keeps_its_reference_counts(monkeypatch):
    async def fake_ka(payload, request):
        page = _ka_page()
        # Ohne auflösbares Konvolut bleibt die Referenzzählung unangetastet.
        page["listings"] = [page["listings"][0]]
        page["pagination"]["unique_listings"] = 1
        page["summary"].update({"fetched_listings": 1, "visible_listings": 1, "reported_total": 1})
        return page

    async def fail_detail(url: str) -> str:
        raise AssertionError("Detailseite darf ohne Konvolut nicht geladen werden")

    monkeypatch.setattr(service.reference, "search_page", fake_ka)
    monkeypatch.setattr(service, "_fetch_detail_html", fail_detail)
    payload = service.SearchRequest.model_validate(
        {"mode": "live", "query": "snes spiele", "page": 0, "source": "kleinanzeigen", "include_review": True, "include_rejected": True}
    )
    result = asyncio.run(service.search_page(payload, None))
    assert result["summary"]["fetched_listings"] == 1
    assert result["summary"]["visible_listings"] == len(result["listings"]) == 1
