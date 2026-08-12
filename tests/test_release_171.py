from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_background_batches_run_two_at_a_time():
    source = read("cloudflare/public/vinted-background-132.js")
    assert "const BATCH_CONCURRENCY = 2;" in source
    assert "const BATCH_SIZE = 3;" in source
    assert "Array.from({length: BATCH_CONCURRENCY}, () => processQueue(token))" in source


def test_every_request_owns_its_abort_controller():
    # A shared controller would leave all but the last parallel batch
    # unabortable when a new run supersedes the current one.
    source = read("cloudflare/public/vinted-background-132.js")
    assert "const controllers = new Set();" in source
    assert "controllers.add(active);" in source
    assert "controllers.delete(active);" in source
    assert "for (const active of controllers) active.abort();" in source


def test_parallel_batches_treat_a_rate_limit_as_retryable():
    source = read("cloudflare/public/vinted-background-132.js")
    assert "const rateLimited = status === 429;" in source
    assert "if (rateLimited) await sleep(1500);" in source


def test_primary_search_still_wins_over_background_details():
    source = read("cloudflare/public/vinted-background-132.js")
    # The guard has to sit inside the worker loop, otherwise only the first
    # worker would yield while the others keep requesting.
    worker = source.split("async function processQueue(token)")[1]
    assert "if (window.GP_SEARCH_RUNNING === true)" in worker
    assert "typeof stopRequested !== 'undefined' && stopRequested" in worker


def test_version_metadata_reports_the_new_concurrency():
    metadata = json.loads(read("VERSION.json"))
    vinted = metadata["sources"]["vinted"]
    assert vinted["background_batch_concurrency"] == 2
    assert vinted["background_batch_size"] == 3
    assert vinted["yields_to_primary_search"] is True
    assert metadata["verification"]["vinted_background_batch_concurrency"] == 2
