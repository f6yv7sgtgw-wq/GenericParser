"""GenericParser 0.42.3 – app-free service with reported-total pagination guard."""
from __future__ import annotations

from . import cloudflare_v0422 as bootstrap

VERSION = "0.42.3"
BUILD_ID = "gp-0423-20260802-1"
BUILD_REVISION = BUILD_ID
API_CONTRACT = "match-v6.1-page-worker"
SERVICE_MODULE = "generic_parser.search_service_v0423"

bootstrap.VERSION = VERSION
bootstrap.BUILD_ID = BUILD_ID
bootstrap.BUILD_REVISION = BUILD_REVISION
bootstrap.API_CONTRACT = API_CONTRACT
bootstrap.SERVICE_MODULE = SERVICE_MODULE
bootstrap._service = None
bootstrap._import_error = None

app = bootstrap.app

__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
