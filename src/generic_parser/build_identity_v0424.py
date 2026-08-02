"""Single source of truth for GenericParser 0.42.4 build identity."""
VERSION = "0.42.4"
BUILD_ID = "gp-0424-20260802-1"
BUILD_REVISION = BUILD_ID
API_CONTRACT = "match-v6.1-page-worker"
WORKER_UNIT = "bootstrap+app-free-one-page-service+pagination-guard+shared-identity"


def as_dict() -> dict[str, str]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "build_revision": BUILD_REVISION,
        "api_contract": API_CONTRACT,
        "worker_unit": WORKER_UNIT,
    }
