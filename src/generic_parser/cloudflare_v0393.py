"""GenericParser 0.39.3 – adaptive, resource-aware page search."""

from __future__ import annotations

from . import cloudflare_v039 as page_worker

# Keep the proven one-page Worker contract. Resource pacing, adaptive pauses,
# retries, consistency aggregation and bounded DOM rendering are client-side,
# so every Worker invocation still handles exactly one Kleinanzeigen page.
page_worker.VERSION = "0.39.3"
app = page_worker.app

__all__ = ["app"]
