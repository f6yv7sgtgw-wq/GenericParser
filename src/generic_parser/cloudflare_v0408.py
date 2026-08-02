"""GenericParser 0.40.8 – page-level client diagnostics on stable worker core."""
from __future__ import annotations
from . import cloudflare_v039 as page_worker
VERSION = "0.40.8"
page_worker.VERSION = VERSION
app = page_worker.app
__all__ = ["app"]
