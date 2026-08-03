"""Single source of truth for GenericParser 0.43.1."""
VERSION = "0.43.1"
BUILD_ID = "gp-0431-20260803-1"
BUILD_REVISION = "pending-github-commit"
API_CONTRACT = "match-v6.3-single-identity-worker"
ENTRYPOINT = "generic_parser.cloudflare_worker:Default.fetch"
BOOTSTRAP_MODULE = "generic_parser.cloudflare_v0431"
SEARCH_MODULE = "generic_parser.search_service_v0431"
IDENTITY_SCHEMA = 1


def identity(component: str) -> dict[str, object]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "build_revision": BUILD_REVISION,
        "api_contract": API_CONTRACT,
        "entrypoint": ENTRYPOINT,
        "bootstrap_module": BOOTSTRAP_MODULE,
        "search_module": SEARCH_MODULE,
        "component": component,
        "identity_schema": IDENTITY_SCHEMA,
    }
