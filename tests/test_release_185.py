"""Turnus über die Quellen und die deterministische Fallsammlung."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generic_parser import vinted_adapter
from generic_parser.kleinanzeigen_bundles import parse_bundle_items
from generic_parser.module_api_v2 import _advance_state
from generic_parser.normalization import normalize_condition, normalize_delivery_mode


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/normalization_cases.json").read_text(encoding="utf-8"))

SOURCES = ["kleinanzeigen", "vinted", "ebay"]


def _request(sources: list[str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(searches=[SimpleNamespace(sources=sources or SOURCES)])


def _fresh_state() -> dict:
    return {
        "search_index": 0,
        "source_index": 0,
        "page": 0,
        "pages_processed": 0,
        "listings_returned": 0,
        "searches_complete": 0,
        "sources_complete": 0,
        "failed_sources": 0,
        "degraded": False,
    }


def _run(limits: dict[str, int], *, state: dict | None = None, sources: list[str] | None = None) -> list[str]:
    """Fährt Pakete, bis der Stapel fertig ist, und protokolliert Quelle+Seite."""

    request = _request(sources)
    names = sources or SOURCES
    state = state or _fresh_state()
    seen: dict[str, int] = {}
    order: list[str] = []
    for step in range(40):
        source = names[state["source_index"]]
        page = int(state["page"])
        seen[source] = seen.get(source, 0) + 1
        order.append(f"{source}:{page}")
        complete = seen[source] >= limits[source]
        state, batch_complete, _ = _advance_state(
            state,
            request,
            page_complete=complete,
            next_page=None if complete else page + 1,
            failed=False,
            degraded=False,
            listings=25,
            # Große Zeitschritte: Die Vinted-Abklingzeit (1.9.1) ist hier nie
            # aktiv, diese Suite prüft die reine Rotationsmechanik.
            now=step * 60.0,
        )
        if batch_complete:
            break
    return order


def test_sources_take_turns_instead_of_being_drained_one_after_another():
    order = _run({"kleinanzeigen": 3, "vinted": 3, "ebay": 3})
    assert order[:6] == [
        "kleinanzeigen:0",
        "vinted:0",
        "ebay:0",
        "kleinanzeigen:1",
        "vinted:1",
        "ebay:1",
    ]


def test_each_source_resumes_at_its_own_page_after_a_rotation():
    order = _run({"kleinanzeigen": 2, "vinted": 3, "ebay": 1})
    # eBay fällt nach seiner einzigen Seite heraus, Kleinanzeigen nach zweien;
    # Vinted läuft allein weiter und zählt dabei korrekt hoch.
    assert order == [
        "kleinanzeigen:0",
        "vinted:0",
        "ebay:0",
        "kleinanzeigen:1",
        "vinted:1",
        "vinted:2",
    ]


def test_an_exhausted_source_is_not_visited_again():
    order = _run({"kleinanzeigen": 1, "vinted": 4, "ebay": 1})
    assert order.count("kleinanzeigen:0") == 1
    assert not [entry for entry in order if entry.startswith("kleinanzeigen:1")]
    assert [entry for entry in order if entry.startswith("vinted")] == [
        "vinted:0",
        "vinted:1",
        "vinted:2",
        "vinted:3",
    ]


def test_a_single_source_search_still_pages_straight_through():
    order = _run({"vinted": 3}, sources=["vinted"])
    assert order == ["vinted:0", "vinted:1", "vinted:2"]


def test_an_older_continuation_token_without_cursors_keeps_working():
    # Token aus einem Lauf vor 1.8.5: kein source_pages, kein sources_done.
    legacy = _fresh_state()
    legacy["source_index"] = 1
    legacy["page"] = 2
    order = _run({"kleinanzeigen": 1, "vinted": 3, "ebay": 1}, state=legacy)
    assert order[0] == "vinted:2"
    assert "kleinanzeigen:0" in order and "ebay:0" in order


def test_every_source_completes_exactly_once():
    request = _request()
    state = _fresh_state()
    limits = {"kleinanzeigen": 2, "vinted": 2, "ebay": 2}
    seen: dict[str, int] = {}
    for _ in range(40):
        source = SOURCES[state["source_index"]]
        seen[source] = seen.get(source, 0) + 1
        complete = seen[source] >= limits[source]
        state, batch_complete, _ = _advance_state(
            state,
            request,
            page_complete=complete,
            next_page=None if complete else int(state["page"]) + 1,
            failed=False,
            degraded=False,
            listings=25,
        )
        if batch_complete:
            break
    assert state["sources_complete"] == len(SOURCES)
    assert state["searches_complete"] == 1


@pytest.mark.parametrize("phrase,expected", [tuple(case) for case in CASES["condition"]])
def test_condition_fixtures(phrase, expected):
    assert normalize_condition(phrase) == expected


@pytest.mark.parametrize("raw,expected", [tuple(case) for case in CASES["size"]])
def test_size_fixtures(raw, expected):
    assert vinted_adapter._size_text(raw) == expected


@pytest.mark.parametrize("payload,expected", [tuple(case) for case in CASES["delivery"]])
def test_delivery_fixtures(payload, expected):
    assert normalize_delivery_mode(**payload) == expected


@pytest.mark.parametrize("case", CASES["bundle"], ids=[case["name"] for case in CASES["bundle"]])
def test_bundle_fixtures(case):
    items = [(item["title"], item["price"]) for item in parse_bundle_items(case["description"])]
    assert items == [tuple(entry) for entry in case["expected"]]


def test_condition_rules_stay_free_of_punctuation():
    """Nadeln mit Interpunktion könnten nach der Vereinheitlichung nie treffen."""

    import re

    from generic_parser import normalization

    offenders = [
        needle
        for _, needles in normalization._CONDITION_RULES
        for needle in needles
        if re.search(r"[^0-9a-zäöüß ]", needle)
    ]
    assert offenders == []


def test_size_length_limit_matches_the_vinted_worker():
    worker = (ROOT / "pocs/vinted-browser/src/index.js").read_text(encoding="utf-8")
    assert "size.length<=12" in worker
    assert vinted_adapter._SIZE_MAX_LENGTH == 12
