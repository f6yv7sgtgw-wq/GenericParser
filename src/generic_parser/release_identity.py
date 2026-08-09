"""Single source of truth for the active GenericParser release.

Compatibility/runtime modules may keep historical filenames, but public release
identity must be imported from here. Do not duplicate VERSION/BUILD_ID in
workflows, tests, browser assets or transport wrappers.
"""

VERSION = "1.3.0"
BUILD_ID = "gp-130-20260808-1"
API_CONTRACT = "generic-parser-module-v1"
MODULE_CONTRACT = API_CONTRACT
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v111_runtime"
SEARCH_RUNTIME = "0.45.0+multisource-runtime-bridge"
WORKER_UNIT = "stable-paid+runtime-bridge+kleinanzeigen+vinted-service-binding-detail-enrichment+evercade-snes+module-v1"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "service-binding+runtime-loaded-public-identity+vinted-detail-enrichment+multisource-diagnostics"
RELEASE_DATE = "2026-08-08"
WORKER_PLAN = "paid"
