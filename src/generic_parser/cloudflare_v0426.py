"""GenericParser 0.42.6 rollback bootstrap.

Restores the proven 0.42.4/0.42.3 search transport and removes the
0.42.5 FFI transport and global monkey patching.
"""
from __future__ import annotations
from . import cloudflare_v0422 as bootstrap
from .build_identity_v0426 import VERSION, BUILD_ID, BUILD_REVISION, API_CONTRACT

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
