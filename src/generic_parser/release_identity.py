"""Single source of truth for the active GenericParser release.

Compatibility/runtime modules may keep historical filenames, but public release
identity must be imported from here. Do not duplicate VERSION/BUILD_ID in
workflows, tests, browser assets or transport wrappers.
"""

VERSION = "1.6.5"
BUILD_ID = "gp-165-20260812-1"
API_CONTRACT = "generic-parser-module-v1"
MODULE_CONTRACT = API_CONTRACT
PREFERRED_MODULE_CONTRACT = "generic-parser-module-v2"
SUPPORTED_MODULE_CONTRACTS = (MODULE_CONTRACT, PREFERRED_MODULE_CONTRACT)
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0452"
SEARCH_MODULE = "generic_parser.search_service_v111_runtime"
SEARCH_RUNTIME = "0.45.0+multisource-runtime-bridge"
WORKER_UNIT = "stable-paid+runtime-bridge+three-sources+product-classification+result-filters+explicit-browser-favorites+signed-ebay-deletion-endpoint+truthful-stop-status+fail-open-browser-startup+mobile-transport-recovery+web-ui-162+module-v1+module-v2"
FUNCTIONAL_REFERENCE = "0.44.4"
OPERATIONAL_REFERENCE = "0.44.6.5"
RUNTIME_REFERENCE = "0.44.6.2"
TECHNICAL_BASE = "three-source-orchestration+product-classification-v1+traffic-group-sort+browser-local-explicit-favorites+ebay-ecdsa-deletion-notifications+truthful-stop-status+fail-open-identity+mobile-transport-recovery+deferred-vinted-details+responsive-web-ui-162+signed-continuations-v2"
RELEASE_DATE = "2026-08-12"
WORKER_PLAN = "paid"
