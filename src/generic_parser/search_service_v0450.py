"""GenericParser module service with multi-source search on the stable 0.44.4 core."""
from __future__ import annotations

from typing import Any

from fastapi import Request

from . import search_service_v0444 as reference
from .build_identity_v0450 import (
    API_CONTRACT,
    BUILD_ID,
    FUNCTIONAL_REFERENCE,
    OPERATIONAL_REFERENCE,
    RUNTIME_REFERENCE,
    SEARCH_MODULE,
    VERSION,
    WORKER_UNIT,
)
from .integrations import evercade_profile, snes_pal_profile
from .module_api import (
    MODULE_CONTRACT,
    DebugTrace,
    ModulePageRequest,
    ModulePageResponse,
    ModuleSearchProfile,
    module_response_from_legacy,
    run_contract_self_tests,
)
from .vinted_adapter import search_vinted

SearchRequest = reference.SearchRequest
_MULTI_SOURCES = {"auto", "multi-source", "all", "both"}


def identity() -> dict[str, Any]:
    return {
        "version": VERSION,
        "build_id": BUILD_ID,
        "api_contract": API_CONTRACT,
        "module_contract": MODULE_CONTRACT,
        "worker_unit": WORKER_UNIT,
        "search_module": SEARCH_MODULE,
        "reference_version": FUNCTIONAL_REFERENCE,
        "operational_reference": OPERATIONAL_REFERENCE,
        "runtime_reference": RUNTIME_REFERENCE,
        "search_behavior_changed": True,
        "sources": ["kleinanzeigen", "vinted"],
        "default_sources": ["kleinanzeigen", "vinted"],
    }


def header_enabled(request: Request, name: str) -> bool:
    return request.headers.get(name, "").strip().casefold() in {"1", "true", "yes", "on"}


def _include_listing(listing: dict[str, Any], payload: SearchRequest) -> bool:
    decision = str((listing.get("match") or {}).get("decision") or "review")
    if decision == "reject" and not bool(getattr(payload, "include_rejected", True)):
        return False
    if decision == "review" and not bool(getattr(payload, "include_review", True)):
        return False
    return True


def _decorate_vinted(listing: dict[str, Any], payload: SearchRequest) -> dict[str, Any]:
    evaluation = reference._evaluate(listing, payload)
    listing["traffic_light"] = evaluation
    listing["match"] = {
        "listing_class": evaluation["label"],
        "score": evaluation["score"],
        "decision": evaluation["decision"],
        "reason": evaluation["reason"],
    }
    return listing


async def _multi_source_search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    source = str(getattr(payload, "source", "auto") or "auto").casefold()
    want_ka = source in _MULTI_SOURCES or source in {"kleinanzeigen", "ka"}
    want_vinted = source in _MULTI_SOURCES or source == "vinted"
    page = int(getattr(payload, "page", 0) or 0)

    ka_result: dict[str, Any] | None = None
    if want_ka:
        # Preserve the proven Kleinanzeigen core exactly. For multi-source mode
        # the reference receives auto so its established pagination still works.
        ka_payload = payload.model_copy(update={"source": "auto"}) if hasattr(payload, "model_copy") else payload
        ka_result = await reference.search_page(ka_payload, request)
        for item in ka_result.get("listings") or []:
            item.setdefault("source", "kleinanzeigen")
            item.setdefault("source_label", "Kleinanzeigen")

    vinted_result: dict[str, Any] | None = None
    vinted_visible: list[dict[str, Any]] = []
    vinted_hidden = 0
    vinted_counts = {"green": 0, "yellow": 0, "red": 0}
    if want_vinted:
        vinted_result = await search_vinted(str(payload.query), page=page)
        for raw in vinted_result.get("listings") or []:
            item = _decorate_vinted(raw, payload)
            color = str((item.get("traffic_light") or {}).get("color") or "yellow")
            if color in vinted_counts:
                vinted_counts[color] += 1
            if _include_listing(item, payload):
                vinted_visible.append(item)
            else:
                vinted_hidden += 1

    if not ka_result:
        ka_result = {
            "listings": [],
            "pagination": {"current_page": page, "next_page": None, "complete": True, "source": "kleinanzeigen", "unique_listings": 0},
            "summary": {"fetched_listings": 0, "visible_listings": 0, "hidden_by_filter": 0, "reported_total": None},
            "traffic_light_summary": {"green": 0, "yellow": 0, "red": 0},
            "generated_urls": [],
            "worker": {},
        }

    ka_listings = list(ka_result.get("listings") or [])
    ka_summary = ka_result.get("summary") if isinstance(ka_result.get("summary"), dict) else {}
    ka_pagination = ka_result.get("pagination") if isinstance(ka_result.get("pagination"), dict) else {}
    ka_counts = ka_result.get("traffic_light_summary") if isinstance(ka_result.get("traffic_light_summary"), dict) else {}

    combined = ka_listings + vinted_visible
    ka_hidden = int(ka_summary.get("hidden_by_filter") or 0)
    ka_fetched = int(ka_summary.get("fetched_listings") or len(ka_listings) + ka_hidden)
    vinted_fetched = len(vinted_visible) + vinted_hidden
    fetched = ka_fetched + vinted_fetched
    hidden = ka_hidden + vinted_hidden

    ka_next = ka_pagination.get("next_page") if want_ka else None
    vi_next = vinted_result.get("next_page") if vinted_result and want_vinted else None
    next_candidates = [int(value) for value in (ka_next, vi_next) if value is not None]
    next_page = min(next_candidates) if next_candidates else None
    complete = next_page is None

    generated_urls = list(ka_result.get("generated_urls") or [])
    if vinted_result and vinted_result.get("url"):
        generated_urls.append(vinted_result["url"])

    source_status = {
        "kleinanzeigen": {
            "enabled": want_ka,
            "status": "ok" if want_ka else "disabled",
            "visible": len(ka_listings),
            "hidden": ka_hidden,
        },
        "vinted": {
            "enabled": want_vinted,
            "status": (vinted_result or {}).get("status", "disabled" if not want_vinted else "degraded"),
            "visible": len(vinted_visible),
            "hidden": vinted_hidden,
            "http_status": (vinted_result or {}).get("http_status"),
            "reason": (vinted_result or {}).get("reason"),
        },
    }

    result = dict(ka_result)
    result["listings"] = combined
    result["pagination"] = {
        **ka_pagination,
        "current_page": page,
        "next_page": next_page,
        "complete": complete,
        "source": "multi-source" if want_ka and want_vinted else ("vinted" if want_vinted else "kleinanzeigen"),
        "unique_listings": fetched,
        "stop_reason": None if not complete else "all_sources_complete",
    }
    result["summary"] = {
        **ka_summary,
        "fetched_listings": fetched,
        "visible_listings": len(combined),
        "hidden_by_filter": hidden,
        "reported_total": ka_summary.get("reported_total"),
        "sources": source_status,
    }
    result["traffic_light_summary"] = {
        color: int(ka_counts.get(color) or 0) + vinted_counts[color]
        for color in ("green", "yellow", "red")
    }
    result["source_status"] = source_status
    result["generated_urls"] = generated_urls
    result["worker"] = {**(result.get("worker") or {}), **identity()}
    result["deployment_identity"] = identity()
    return result


async def search_page(payload: SearchRequest, request: Request) -> dict[str, Any]:
    """Kompatibilitätsroute: auto searches Kleinanzeigen and Vinted."""
    return await _multi_source_search(payload, request)


async def search_module_page(
    payload: ModulePageRequest,
    request: Request,
) -> ModulePageResponse:
    """Öffentliche module-v1-Seitensuche über die aktivierten Quellen."""

    debug_options = payload.debug
    if header_enabled(request, "x-genericparser-debug") and not debug_options.enabled:
        debug_options = debug_options.model_copy(update={"enabled": True})

    trace_id = request.headers.get("cf-ray") or request.headers.get("x-request-id") or "local"
    trace = DebugTrace(debug_options, trace_id)
    trace.mark("module_request_validated", page=payload.page, source=payload.source)
    legacy_dict = payload.profile.to_legacy_payload(page=payload.page, source=payload.source)
    legacy_payload = SearchRequest.model_validate(legacy_dict)
    trace.mark("legacy_payload_validated")
    result = await _multi_source_search(legacy_payload, request)
    trace.mark("multi_source_search_completed", sources=["kleinanzeigen", "vinted"])
    result["deployment_identity"] = identity()
    result["worker"] = {**(result.get("worker") or {}), **identity()}
    return module_response_from_legacy(result, payload, trace)


def validate_module_profile(profile: ModuleSearchProfile) -> dict[str, Any]:
    """Validiert auch gegen den unveränderten 0.44.4-Requestvertrag."""

    legacy_payload = profile.to_legacy_payload()
    validated = SearchRequest.model_validate(legacy_payload)
    return {
        "contract": MODULE_CONTRACT,
        "valid": True,
        "profile": profile.model_dump(mode="json"),
        "legacy_payload": validated.model_dump(mode="json", exclude_none=True),
        "empty_fields_ignored": True,
        "reference_request_validated": True,
        "default_sources": ["kleinanzeigen", "vinted"],
    }


def run_module_self_tests() -> dict[str, Any]:
    result = run_contract_self_tests()
    adapter_checks: list[dict[str, Any]] = []

    evercade = evercade_profile("Interplay Collection 1", market_value=30)
    adapter_checks.append(
        {
            "name": "evercade_adapter",
            "ok": evercade.query.startswith("Evercade ") and evercade.market_value == 30,
        }
    )
    snes = snes_pal_profile("Super Metroid", market_value=70)
    adapter_checks.append(
        {
            "name": "snes_adapter",
            "ok": "PAL" in snes.required_terms and "NTSC" in snes.excluded_terms,
        }
    )
    adapter_checks.append(
        {
            "name": "multi_source_default",
            "ok": identity()["default_sources"] == ["kleinanzeigen", "vinted"],
        }
    )
    result["checks"].extend(adapter_checks)
    result["ok"] = bool(result["ok"] and all(item["ok"] for item in adapter_checks))
    result["deployment"] = identity()
    return result


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
