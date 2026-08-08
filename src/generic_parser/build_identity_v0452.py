"""Deployment identity for GenericParser 1.1.2.

1.1.2 changes only the Vinted adapter: it establishes a normal anonymous
public-web session before catalog HTML/API requests. Kleinanzeigen, the
0.44.4 search core, runtime bridge and generic-parser-module-v1 stay unchanged.
"""

VERSION = "1.1.2"
BUILD_ID = "gp-112-20260808-1"
API_CONTRACT = "generic-parser-module-v1"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v111_runtime"
SEARCH_RUNTIME = "0.45.0+multisource-1.1-runtime-bridge"
WORKER_UNIT = "stable-112-paid+runtime-bridge+kleinanzeigen+vinted-session+evercade-snes+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "1.1.1+vinted-session-bootstrap"
