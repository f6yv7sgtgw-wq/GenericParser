"""Deployment identity for GenericParser 0.45.2 Build 4.

Build 4 keeps the live-proven Build 3 worker/search runtime and fixes only
browser UI/build compatibility and cache-visible release identity.
"""

VERSION = "0.45.2"
BUILD_ID = "gp-0452-20260807-4"
API_CONTRACT = "generic-parser-module-v1"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v0450"
SEARCH_RUNTIME = "0.45.0"
WORKER_UNIT = "transport-0452-build4+search-runtime-0450+reference-04465+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "0.45.0"
