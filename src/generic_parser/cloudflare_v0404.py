"""GenericParser 0.40.4 – stable page-worker hotfix.

This release deliberately imports the proven one-page implementation directly,
avoiding the nested 0.40 -> 0.40.1 -> 0.40.3 wrapper chain that could fail at
runtime initialization. Browser session isolation remains a frontend concern.
"""

from __future__ import annotations

from . import cloudflare_v039 as page_worker

VERSION = "0.40.4"
page_worker.VERSION = VERSION
app = page_worker.app

__all__ = ["app"]
