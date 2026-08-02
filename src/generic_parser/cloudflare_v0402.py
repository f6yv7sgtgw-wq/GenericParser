"""GenericParser 0.40.2 – isolated browser search sessions."""

from __future__ import annotations

from . import cloudflare_v040 as resumable_worker

VERSION = "0.40.2"
resumable_worker.VERSION = VERSION
resumable_worker.page_worker.VERSION = VERSION
app = resumable_worker.app

__all__ = ["app"]
