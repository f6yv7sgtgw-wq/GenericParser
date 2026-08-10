"""Compatibility import path for the active release identity.

Historical module name retained so deployed import paths stay stable. Public
release identity lives only in generic_parser.release_identity.
"""

from .release_identity import (
    API_CONTRACT,
    BOOTSTRAP_MODULE,
    BUILD_ID,
    ENTRYPOINT,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    PREFERRED_MODULE_CONTRACT,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    SEARCH_RUNTIME,
    SUPPORTED_MODULE_CONTRACTS,
    TECHNICAL_BASE,
    VERSION,
    WORKER_UNIT,
)

__all__ = [
    "VERSION", "BUILD_ID", "API_CONTRACT", "ENTRYPOINT", "BOOTSTRAP_MODULE",
    "SEARCH_MODULE", "SEARCH_RUNTIME", "WORKER_UNIT", "FUNCTIONAL_REFERENCE",
    "OPERATIONAL_REFERENCE", "RUNTIME_REFERENCE", "TECHNICAL_BASE",
    "PREFERRED_MODULE_CONTRACT", "SUPPORTED_MODULE_CONTRACTS",
]
