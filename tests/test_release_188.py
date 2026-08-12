from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_search_page_can_write_the_event_log_at_all():
    index = read("cloudflare/public/index.html")
    log_page = read("cloudflare/public/eventlog.html")
    worker = read("cloudflare/public/service-worker.js")
    # Bis 1.8.7 prueften alle Aufrufer nur, ob es den Schreiber gibt - es gab ihn nie.
    assert "./eventlog-writer-188.js" in index
    assert "./eventlog-writer-188.js" in log_page
    assert '"./eventlog-writer-188.js",' in worker
    # Der Schreiber muss vor seinen Aufrufern stehen.
    assert index.index("eventlog-writer-188.js") < index.index("app.js")


def test_the_writer_defines_the_expected_entry_point():
    writer = read("cloudflare/public/eventlog-writer-188.js")
    assert "window.gpEventLog = append;" in writer
    assert "typeof window.gpEventLog !== 'function'" in writer


def test_the_offer_format_reaches_the_card_as_text_not_as_a_contract_code():
    app_js = read("cloudflare/public/app.js")
    assert "const OFFER_FORMAT_LABELS={fixed_price:'Festpreis',auction:'Auktion',best_offer:'Preisvorschlag'};" in app_js
    assert "listing_format:offerFormatLabel(offer.format)" in app_js
    assert "listing_format:offer.format" not in app_js


def test_the_german_labels_keep_the_format_filter_working():
    app_js = read("cloudflare/public/app.js")
    # formatOf sucht in listing_format nach 'auktion' bzw. Preisvorschlag/VB.
    assert "format.includes('auktion')" in app_js
    assert "preisvorschlag" in app_js


def test_version_metadata_requires_a_working_event_log():
    verification = json.loads(read("VERSION.json"))["verification"]
    assert verification["event_log_writer"] == "required"
    assert verification["offer_format_label_localised"] == "required"
