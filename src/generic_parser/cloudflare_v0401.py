"""GenericParser 0.40.1 – pagination fingerprint guard."""

from __future__ import annotations

from . import cloudflare_v040 as production_worker

VERSION = "0.40.1"
production_worker.VERSION = VERSION
production_worker.page_worker.VERSION = VERSION
app = production_worker.app

__all__ = ["app"]
