"""GenericParser 0.42.5 bootstrap with native Workers Fetch transport."""
from __future__ import annotations
from . import cloudflare_v0422 as bootstrap
from .build_identity_v0425 import VERSION, BUILD_ID, BUILD_REVISION, API_CONTRACT

SERVICE_MODULE = "generic_parser.search_service_v0425"
bootstrap.VERSION = VERSION
bootstrap.BUILD_ID = BUILD_ID
bootstrap.BUILD_REVISION = BUILD_REVISION
bootstrap.API_CONTRACT = API_CONTRACT
bootstrap.SERVICE_MODULE = SERVICE_MODULE
bootstrap._service = None
bootstrap._import_error = None
app = bootstrap.app

__all__ = ["app", "VERSION", "BUILD_ID", "BUILD_REVISION", "API_CONTRACT"]
