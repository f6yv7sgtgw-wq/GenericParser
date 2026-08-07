"""0.45.2 search bootstrap on the proven 0.45.0 ASGI application.

This module intentionally reuses the live-proven 0.45.0 FastAPI app and only
adds the two browser-friendly aliases introduced by 0.45.1. No search,
matching, ranking, pricing, pagination or recovery code is changed.
"""
from __future__ import annotations

from .cloudflare_v0450 import app, legacy_search, module_search

# Keep canonical 0.45.0 routes untouched; only register aliases.
app.add_api_route("/search", legacy_search, methods=["POST"], include_in_schema=True)
app.add_api_route("/api/module/search", module_search, methods=["POST"], include_in_schema=True)
