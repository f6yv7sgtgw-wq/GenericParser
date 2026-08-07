"""Deployment identity for GenericParser 0.45.2 Build 7.

Build 7 keeps the Build 6 Evercade compatibility and the live-proven 0.45.0
search runtime unchanged. It removes browser-side Free Worker pacing for the
paid Cloudflare Worker profile.
"""

VERSION = "0.45.2"
BUILD_ID = "gp-0452-20260808-7"
API_CONTRACT = "generic-parser-module-v1"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v0450"
SEARCH_RUNTIME = "0.45.0"
WORKER_UNIT = "transport-0452-build7-paid+evercade-compat+search-runtime-0450+reference-04465+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "0.45.0"
