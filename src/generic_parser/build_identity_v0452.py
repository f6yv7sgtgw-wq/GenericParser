"""Deployment identity for GenericParser 1.1.1.

1.1.1 fixes the 1.1.0 search-service identity mismatch with a compatibility
bridge. The multi-source search behavior, Vinted adapter, Kleinanzeigen 0.44.4
core and generic-parser-module-v1 contract remain unchanged.
"""

VERSION = "1.1.1"
BUILD_ID = "gp-111-20260808-1"
API_CONTRACT = "generic-parser-module-v1"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v111_runtime"
SEARCH_RUNTIME = "0.45.0+multisource-1.1-runtime-bridge"
WORKER_UNIT = "stable-111-paid+runtime-bridge+kleinanzeigen+vinted+evercade-snes+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "1.1.0+runtime-identity-hotfix"
