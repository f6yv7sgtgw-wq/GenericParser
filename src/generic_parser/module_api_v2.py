"""GenericParser module API v2.

The v2 contract is deliberately project independent.  It processes one source
page per HTTP request and returns a signed continuation token for the next
packet.  Cartridge catalogues, market values and project traffic lights remain
outside GenericParser.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import time
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .module_api import ModuleDebugOptions, ModuleSearchProfile
from .release_identity import PREFERRED_MODULE_CONTRACT


MODULE_CONTRACT_V2 = PREFERRED_MODULE_CONTRACT
CONTINUATION_TTL_SECONDS = 2 * 60 * 60
DEFAULT_SOURCES = ["kleinanzeigen", "vinted", "ebay"]
SourceName = Literal["kleinanzeigen", "vinted", "ebay"]
SortName = Literal["relevance", "date", "price_asc", "price_desc"]


def _normalize_terms(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("terms must be an array or comma-separated string")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


class V2Client(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = Field(min_length=1, max_length=80)
    project_version: str = Field(min_length=1, max_length=40)


class V2Criteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_terms: list[str] = Field(default_factory=list)
    excluded_terms: list[str] = Field(default_factory=list)
    model_patterns: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)

    @field_validator(
        "required_terms",
        "excluded_terms",
        "model_patterns",
        "brands",
        mode="before",
    )
    @classmethod
    def normalize_terms(cls, value: Any) -> list[str]:
        return _normalize_terms(value)


class V2Location(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0)

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        if value in {None, ""}:
            return None
        if len(value) != 5 or not value.isdigit():
            raise ValueError("postal_code must be a five-digit German postal code")
        return value

    @model_validator(mode="after")
    def validate_location(self) -> "V2Location":
        if (self.postal_code is not None or self.radius_km is not None) and self.location_id is None:
            raise ValueError("postal_code and radius_km require a verified location_id")
        return self


class V2Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_price: float | None = Field(default=None, ge=0)
    accept_bundles: bool = False
    accept_incomplete: bool = False
    include_auctions: bool = False
    include_review: bool = True
    include_rejected: bool = True


class V2SearchDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    search_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=300)
    sources: list[SourceName] = Field(default_factory=lambda: list(DEFAULT_SOURCES), min_length=1, max_length=3)
    criteria: V2Criteria = Field(default_factory=V2Criteria)
    filters: V2Filters = Field(default_factory=V2Filters)
    location: V2Location = Field(default_factory=V2Location)
    sort_by: SortName = "relevance"

    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value: list[SourceName]) -> list[SourceName]:
        result: list[SourceName] = []
        for source in value:
            if source not in result:
                result.append(source)
        return result

    def to_v1_profile(self) -> ModuleSearchProfile:
        """Use the proven v1 profile mapping without importing project data."""

        return ModuleSearchProfile(
            profile_id=self.search_id,
            display_name=self.query,
            query=self.query,
            required_terms=self.criteria.required_terms,
            excluded_terms=self.criteria.excluded_terms,
            model_patterns=self.criteria.model_patterns,
            brands=self.criteria.brands,
            max_price=self.filters.max_price,
            postal_code=self.location.postal_code,
            location_id=self.location.location_id,
            radius_km=self.location.radius_km,
            accept_bundles=self.filters.accept_bundles,
            accept_incomplete=self.filters.accept_incomplete,
            include_ebay_auctions=self.filters.include_auctions,
            include_review=self.filters.include_review,
            include_rejected=self.filters.include_rejected,
            sort_by=self.sort_by,
        )


class V2BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal[MODULE_CONTRACT_V2] = MODULE_CONTRACT_V2
    batch_id: str = Field(min_length=1, max_length=128)
    client: V2Client
    searches: list[V2SearchDefinition] = Field(min_length=1, max_length=100)
    continuation_token: str | None = None
    debug: ModuleDebugOptions = Field(default_factory=ModuleDebugOptions)

    @field_validator("searches")
    @classmethod
    def unique_search_ids(cls, value: list[V2SearchDefinition]) -> list[V2SearchDefinition]:
        identifiers = [item.search_id for item in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("search_id must be unique inside a batch")
        return value


class V2SingleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal[MODULE_CONTRACT_V2] = MODULE_CONTRACT_V2
    batch_id: str = Field(min_length=1, max_length=128)
    client: V2Client
    search: V2SearchDefinition
    continuation_token: str | None = None
    debug: ModuleDebugOptions = Field(default_factory=ModuleDebugOptions)

    def to_batch(self) -> V2BatchRequest:
        return V2BatchRequest(
            batch_id=self.batch_id,
            client=self.client,
            searches=[self.search],
            continuation_token=self.continuation_token,
            debug=self.debug,
        )


class V2ValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal[MODULE_CONTRACT_V2] = MODULE_CONTRACT_V2
    batch_id: str = Field(default="validation", min_length=1, max_length=128)
    client: V2Client
    searches: list[V2SearchDefinition] = Field(min_length=1, max_length=100)

    @field_validator("searches")
    @classmethod
    def unique_search_ids(cls, value: list[V2SearchDefinition]) -> list[V2SearchDefinition]:
        identifiers = [item.search_id for item in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("search_id must be unique inside a batch")
        return value


class ContinuationError(ValueError):
    status_code = 409
    error_code = "CONTINUATION_INVALID"


class ContinuationConflict(ContinuationError):
    status_code = 409
    error_code = "CONTINUATION_CONFLICT"


class ContinuationExpired(ContinuationError):
    status_code = 410
    error_code = "CONTINUATION_EXPIRED"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def continuation_secret() -> bytes:
    """Use a production secret already bound to the Worker.

    A deterministic development key keeps local contract tests usable.  The
    production deployment already requires EBAY_CLIENT_SECRET, so live tokens
    are never signed with the fallback.
    """

    configured = os.getenv("GENERICPARSER_CONTINUATION_SECRET") or os.getenv("EBAY_CLIENT_SECRET")
    return (configured or "genericparser-v2-local-development-only").encode("utf-8")


def request_fingerprint(request: V2BatchRequest) -> str:
    material = {
        "contract": MODULE_CONTRACT_V2,
        "batch_id": request.batch_id,
        "client": request.client.model_dump(mode="json"),
        "searches": [item.model_dump(mode="json") for item in request.searches],
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def encode_continuation(
    state: dict[str, Any],
    *,
    secret: bytes | None = None,
    now: int | None = None,
) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = {
        **state,
        "version": 1,
        "issued_at": issued_at,
        "expires_at": issued_at + CONTINUATION_TTL_SECONDS,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body = _b64encode(raw)
    signature = _b64encode(hmac.new(secret or continuation_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"v2.{body}.{signature}"


def decode_continuation(
    token: str,
    *,
    secret: bytes | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    try:
        prefix, body, signature = token.split(".", 2)
        if prefix != "v2":
            raise ValueError("wrong token version")
        expected = _b64encode(hmac.new(secret or continuation_secret(), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature mismatch")
        payload = json.loads(_b64decode(body))
    except ContinuationError:
        raise
    except Exception as exc:
        raise ContinuationError("continuation token is invalid") from exc
    current = int(time.time() if now is None else now)
    if int(payload.get("expires_at") or 0) < current:
        raise ContinuationExpired("continuation token has expired")
    return payload


def validate_continuation(request: V2BatchRequest) -> dict[str, Any]:
    fingerprint = request_fingerprint(request)
    if not request.continuation_token:
        return {
            "batch_id": request.batch_id,
            "fingerprint": fingerprint,
            "search_index": 0,
            "source_index": 0,
            "page": 0,
            "pages_processed": 0,
            "listings_returned": 0,
            "searches_complete": 0,
            "sources_complete": 0,
            "failed_sources": 0,
            "degraded": False,
        }
    state = decode_continuation(request.continuation_token)
    if state.get("batch_id") != request.batch_id or state.get("fingerprint") != fingerprint:
        raise ContinuationConflict("continuation token does not match this unchanged batch")
    return state


def _source_id(raw_id: Any, source: str, url: str, title: str) -> str:
    value = str(raw_id or "").strip()
    prefix = f"{source}:"
    if value.casefold().startswith(prefix):
        value = value[len(prefix) :]
    if value:
        return value
    return hashlib.sha256(f"{source}|{url}|{title}".encode("utf-8")).hexdigest()[:24]


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def listing_to_v2(raw: dict[str, Any], fallback_source: str) -> dict[str, Any]:
    source = str(raw.get("source") or fallback_source).casefold()
    if source not in DEFAULT_SOURCES:
        source = fallback_source
    title = str(raw.get("title") or "")
    url = str(raw.get("url") or "")
    source_id = _source_id(raw.get("id"), source, url, title)
    item_price = _number(raw.get("item_price"))
    if item_price is None:
        item_price = _number(raw.get("price"))
    shipping = _number(raw.get("shipping_cost"))
    total = _number(raw.get("total_price"))
    if total is None and item_price is not None and (shipping == 0 or raw.get("shipping_available") is False):
        total = item_price
    product = raw.get("product_classification") if isinstance(raw.get("product_classification"), dict) else {}
    match = raw.get("match") if isinstance(raw.get("match"), dict) else {}
    traffic = raw.get("traffic_light") if isinstance(raw.get("traffic_light"), dict) else {}
    result_info = raw.get("result_info") if isinstance(raw.get("result_info"), dict) else {}
    listing_format = str(raw.get("listing_format") or result_info.get("listing_format") or "").casefold()
    if bool(raw.get("auction")) or "auktion" in listing_format:
        offer_format = "auction"
    elif "vb" in listing_format or "preisvorschlag" in listing_format or "best offer" in listing_format:
        offer_format = "best_offer"
    else:
        offer_format = "fixed_price"
    fetched_at = datetime.now(UTC).isoformat()
    return {
        "listing_key": f"{source}:{source_id}",
        "source": source,
        "source_id": source_id,
        "title": title,
        "url": url,
        "image_url": raw.get("image_url"),
        "description": raw.get("description"),
        "pricing": {
            "item": item_price,
            "shipping": shipping,
            "total": total,
            "total_known": total is not None,
            "currency": str(raw.get("currency") or "EUR"),
        },
        "delivery": {
            "shipping_available": raw.get("shipping_available"),
            "pickup_available": True if raw.get("shipping_available") is False else None,
        },
        "location": {
            "postal_code": raw.get("postal_code"),
            "place": raw.get("place"),
        },
        "offer": {
            "format": offer_format,
            "auction": offer_format == "auction",
            "bundle": str(product.get("code") or "") == "bundle"
            or "bundle" in str(result_info.get("scope") or "").casefold()
            or "konvolut" in str(result_info.get("scope") or "").casefold(),
        },
        "classification": {
            "code": str(product.get("code") or result_info.get("product_class") or "unknown"),
            "label": str(product.get("label") or result_info.get("product_class_label") or "Produktart offen"),
            "confidence": str(product.get("confidence") or "unknown"),
            "decision": str(match.get("decision") or "review"),
            "reason": str(match.get("reason") or "Keine Bewertungsdetails verfügbar"),
            "score": _number(match.get("score")),
            "traffic": str(traffic.get("color") or "yellow"),
            "ruleset": str(product.get("ruleset") or "product-classification-v1"),
        },
        "condition": raw.get("condition") or result_info.get("condition"),
        # Additive since 1.7.0: sources without a structured size report null
        # rather than a filler label, so consumers can tell "no size" apart.
        "size": raw.get("size") or result_info.get("size") or None,
        "timestamps": {
            "published_at": raw.get("posted_at"),
            "ends_at": raw.get("item_end_date"),
            "fetched_at": fetched_at,
        },
    }


def normalize_source_status(source: str, raw: dict[str, Any], listing_count: int) -> dict[str, Any]:
    original = str(raw.get("status") or "ok").casefold()
    http_status = raw.get("http_status")
    try:
        status_code = int(http_status or 0)
    except (TypeError, ValueError):
        status_code = 0
    if original == "ok":
        status = "ok" if listing_count else "empty"
    elif original in {"blocked", "rate_limited", "timeout", "unavailable", "partial", "empty", "disabled"}:
        status = original
    elif original in {"degraded", "error", "failed"} and status_code == 429:
        status = "rate_limited"
    elif original in {"degraded", "error", "failed"} and status_code in {401, 403}:
        status = "blocked"
    elif original in {"degraded", "error", "failed"} and status_code in {408, 504}:
        status = "timeout"
    elif original in {"degraded", "error", "failed"}:
        status = "partial" if listing_count else "unavailable"
    else:
        status = "partial"
    retryable = status in {"blocked", "rate_limited", "timeout", "unavailable", "partial"}
    error_code = None
    if status not in {"ok", "empty", "disabled"}:
        error_code = f"SOURCE_HTTP_{http_status}" if http_status else f"SOURCE_{status.upper()}"
    return {
        "source": source,
        "status": status,
        "retryable": retryable,
        "retry_after_ms": raw.get("retry_after_ms"),
        "error_code": error_code,
        "http_status": status_code or None,
        "listings_returned": listing_count,
        "reason": raw.get("reason"),
    }


def _advance_state(
    state: dict[str, Any],
    request: V2BatchRequest,
    *,
    page_complete: bool,
    next_page: int | None,
    failed: bool,
    degraded: bool,
    listings: int,
) -> tuple[dict[str, Any], bool, bool]:
    updated = {
        key: value
        for key, value in state.items()
        if key not in {"version", "issued_at", "expires_at"}
    }
    updated["pages_processed"] = int(updated.get("pages_processed") or 0) + 1
    updated["listings_returned"] = int(updated.get("listings_returned") or 0) + listings
    updated["degraded"] = bool(updated.get("degraded") or degraded)
    if failed:
        updated["failed_sources"] = int(updated.get("failed_sources") or 0) + 1

    completed_search = False
    if not page_complete and next_page is not None:
        updated["page"] = next_page
        return updated, False, False

    updated["sources_complete"] = int(updated.get("sources_complete") or 0) + 1
    search_index = int(updated.get("search_index") or 0)
    source_index = int(updated.get("source_index") or 0) + 1
    current = request.searches[search_index]
    if source_index < len(current.sources):
        updated["source_index"] = source_index
        updated["page"] = 0
        return updated, False, False

    search_index += 1
    updated["search_index"] = search_index
    updated["source_index"] = 0
    updated["page"] = 0
    updated["searches_complete"] = int(updated.get("searches_complete") or 0) + 1
    completed_search = True
    return updated, search_index >= len(request.searches), completed_search


async def execute_v2_packet(
    payload: V2BatchRequest,
    request: Request,
    service: Any,
    *,
    deployment: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    state = validate_continuation(payload)
    search_index = int(state.get("search_index") or 0)
    if search_index >= len(payload.searches):
        raise ContinuationConflict("continuation token already represents a completed batch")
    search = payload.searches[search_index]
    source_index = int(state.get("source_index") or 0)
    if source_index >= len(search.sources):
        raise ContinuationConflict("continuation source cursor is invalid")
    source = search.sources[source_index]
    page = int(state.get("page") or 0)

    profile = search.to_v1_profile()
    legacy_dict = profile.to_legacy_payload(page=page, source=source)
    legacy_payload = service.SearchRequest.model_validate(legacy_dict)
    result = await service.search_page(legacy_payload, request)
    raw_listings = [item for item in (result.get("listings") or []) if isinstance(item, dict)]
    listings = [listing_to_v2(item, source) for item in raw_listings]
    raw_statuses = result.get("source_status") if isinstance(result.get("source_status"), dict) else {}
    source_status = normalize_source_status(
        source,
        raw_statuses.get(source) if isinstance(raw_statuses.get(source), dict) else {},
        len(listings),
    )
    pagination = result.get("pagination") if isinstance(result.get("pagination"), dict) else {}
    next_page_raw = pagination.get("next_page")
    next_page = int(next_page_raw) if next_page_raw is not None else None
    page_complete = bool(pagination.get("complete") is True or next_page is None)
    failed = source_status["status"] in {"blocked", "rate_limited", "timeout", "unavailable"}
    degraded_packet = source_status["status"] in {"blocked", "rate_limited", "timeout", "unavailable", "partial"}
    updated, batch_complete, search_complete = _advance_state(
        state,
        payload,
        page_complete=page_complete,
        next_page=next_page,
        failed=failed,
        degraded=degraded_packet,
        listings=len(listings),
    )
    continuation = None if batch_complete else encode_continuation(updated)
    total_source_packets = sum(len(item.sources) for item in payload.searches)
    all_failed = bool(
        batch_complete
        and int(updated.get("failed_sources") or 0) >= total_source_packets
        and int(updated.get("listings_returned") or 0) == 0
    )
    body = {
        "contract": MODULE_CONTRACT_V2,
        "batch_id": payload.batch_id,
        "status": "complete" if batch_complete else "partial",
        "degraded": bool(updated.get("degraded")),
        "stop_reason": "all_sources_failed" if all_failed else ("batch_complete" if batch_complete else "packet_budget_reached"),
        "progress": {
            "searches_total": len(payload.searches),
            "searches_complete": int(updated.get("searches_complete") or 0),
            "searches_partial": 0 if batch_complete else 1,
            "sources_complete": int(updated.get("sources_complete") or 0),
            "pages_processed": int(updated.get("pages_processed") or 0),
            "listings_returned": int(updated.get("listings_returned") or 0),
        },
        "results": [
            {
                "search_id": search.search_id,
                "status": "complete" if search_complete else "partial",
                "source": source,
                "page": page,
                "listings": listings,
                "sources": {source: source_status},
            }
        ],
        "continuation_token": continuation,
        "deployment": deployment,
    }
    return body, 502 if all_failed else 200


def validate_v2_request(payload: V2ValidateRequest) -> dict[str, Any]:
    batch = V2BatchRequest(
        batch_id=payload.batch_id,
        client=payload.client,
        searches=payload.searches,
    )
    return {
        "contract": MODULE_CONTRACT_V2,
        "valid": True,
        "batch_id": payload.batch_id,
        "searches": [item.model_dump(mode="json") for item in payload.searches],
        "definition_fingerprint": request_fingerprint(batch),
        "empty_fields_ignored": True,
        "packet_model": "one-source-page-per-request",
    }


def v2_capabilities(deployment: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract": MODULE_CONTRACT_V2,
        "previous_contract": "generic-parser-module-v1",
        "sources": list(DEFAULT_SOURCES),
        "default_sources": list(DEFAULT_SOURCES),
        "packet_model": "one-source-page-per-request",
        "batch_limit": 100,
        "continuation": {
            "opaque": True,
            "signed": True,
            "algorithm": "HMAC-SHA256",
            "ttl_seconds": CONTINUATION_TTL_SECONDS,
            "contains_results": False,
        },
        "listing_key": "source:source_id",
        "pricing": "item-plus-known-shipping-with-total_known",
        "persistent_server_jobs": False,
        "web_ui_client": True,
        "deployment": deployment,
    }


__all__ = [
    "MODULE_CONTRACT_V2",
    "CONTINUATION_TTL_SECONDS",
    "ContinuationConflict",
    "ContinuationError",
    "ContinuationExpired",
    "V2BatchRequest",
    "V2SingleRequest",
    "V2ValidateRequest",
    "decode_continuation",
    "encode_continuation",
    "execute_v2_packet",
    "listing_to_v2",
    "request_fingerprint",
    "v2_capabilities",
    "validate_v2_request",
]
