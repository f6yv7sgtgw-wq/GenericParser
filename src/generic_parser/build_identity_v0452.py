"""Deployment identity for GenericParser 1.1.0.

1.1.0 adds Vinted as a second default source beside Kleinanzeigen while
preserving the generic-parser-module-v1 contract and the proven Kleinanzeigen
search core. Vinted uses a public catalog HTML strategy with explicit degraded
source reporting when unavailable.
"""

VERSION = "1.1.0"
BUILD_ID = "gp-110-20260808-1"
API_CONTRACT = "generic-parser-module-v1"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v0450"
SEARCH_RUNTIME = "0.45.0+multisource-1.1"
WORKER_UNIT = "stable-110-paid+kleinanzeigen+vinted+evercade-snes+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "1.0.0+vinted-multisource-fix"
