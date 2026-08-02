"""GenericParser 0.40.3 – integrated browser session lifecycle."""

from __future__ import annotations

from . import cloudflare_v0401 as page_worker

VERSION = "0.40.3"
page_worker.VERSION = VERSION
app = page_worker.app

__all__ = ["app"]
