"""GenericParser 0.39.2 – paced browser-controlled page search."""

from __future__ import annotations

from . import cloudflare_v039 as page_worker

# Reuse the stable one-page worker from 0.39.1. The new pacing, page targets,
# countdown and stop controls live in the browser, so every Worker request
# remains resource-safe and processes exactly one result page.
page_worker.VERSION = "0.39.2"
app = page_worker.app

__all__ = ["app"]
