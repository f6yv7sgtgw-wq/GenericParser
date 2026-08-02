"""GenericParser 0.42.1 – lazy bootstrap with consistent UI-state build identity."""
from __future__ import annotations

from . import cloudflare_v042 as bootstrap

VERSION = "0.42.1"
BUILD_ID = "gp-0421-20260802-1"
BUILD_REVISION = BUILD_ID
API_CONTRACT = "match-v6.1-page-worker"

# The 0.42 bootstrap reads these module globals at request time. Updating them
# keeps readiness, search responses and identity headers on one build without
# importing the search stack during worker startup.
bootstrap.VERSION = VERSION
bootstrap.BUILD_ID = BUILD_ID
bootstrap.BUILD_REVISION = BUILD_REVISION
bootstrap.API_CONTRACT = API_CONTRACT

app = bootstrap.app

__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
