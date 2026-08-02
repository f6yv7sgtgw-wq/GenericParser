"""GenericParser 0.40.7 – stable direct page worker.

This release intentionally bypasses all diagnostic middleware and wrapper chains.
The browser owns session lifecycle, graceful stop, cooldown, and event logging.
"""
from __future__ import annotations

from . import cloudflare_v039 as page_worker

VERSION = "0.40.7"
page_worker.VERSION = VERSION
app = page_worker.app

__all__ = ["app"]
