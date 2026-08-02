"""GenericParser 0.40.6 – graceful-stop and event-log release."""
from __future__ import annotations
from . import cloudflare_v0405 as diagnostic_worker
VERSION = "0.40.6"
diagnostic_worker.VERSION = VERSION
diagnostic_worker.page_worker.VERSION = VERSION
app = diagnostic_worker.app
__all__ = ["app"]
