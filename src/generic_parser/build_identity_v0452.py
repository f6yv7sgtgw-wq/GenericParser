"""Deployment identity for GenericParser 1.0.0.

1.0.0 promotes the live-proven 0.45.2 Build 7 Paid Worker baseline to the
first stable production release. The 0.45.0 search runtime and the 0.44.6.5
operational reference remain unchanged.
"""

VERSION = "1.0.0"
BUILD_ID = "gp-100-20260808-1"
API_CONTRACT = "generic-parser-module-v1"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v0450"
SEARCH_RUNTIME = "0.45.0"
WORKER_UNIT = "stable-100-paid+evercade-snes-compat+search-runtime-0450+reference-04465+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "0.45.2-build7-paid"
