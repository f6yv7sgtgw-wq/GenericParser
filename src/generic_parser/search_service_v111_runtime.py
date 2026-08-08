"""Compatibility bridge for GenericParser 1.1.1.

The legacy 0.45.0 FastAPI bootstrap validates the imported search module against
its own runtime identity. This bridge preserves that expected runtime identity
while delegating all search behavior to the unchanged multi-source service.
"""
from __future__ import annotations

from .build_identity_v0450 import API_CONTRACT, BUILD_ID, VERSION
from .search_service_v0450 import (
    SearchRequest,
    run_module_self_tests,
    search_module_page,
    search_page,
    validate_module_profile,
)

__all__ = [
    "SearchRequest",
    "search_page",
    "search_module_page",
    "validate_module_profile",
    "run_module_self_tests",
    "VERSION",
    "BUILD_ID",
    "API_CONTRACT",
]
