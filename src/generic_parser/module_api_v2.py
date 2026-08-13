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
from .normalization import normalize_condition, normalize_delivery_mode
from .release_identity import PREFERRED_MODULE_CONTRACT


MODULE_CONTRACT_V2 = PREFERRED_MODULE_CONTRACT
CONTINUATION_TTL_SECONDS = 2 * 60 * 60
DEFAULT_SOURCES = ["kleinanzeigen", "vinted", "ebay"]
# Vinted begrenzt den anonymen Katalogzugriff über ein Zeitfenster (belegt
# durch drei Läufe, die nach 11, 6 und 4 Paketen blockiert wurden). Die
# Rotation lässt Vinted deshalb aussetzen, bis die Abklingzeit verstrichen
# ist; die anderen Quellen rotieren pausenlos weiter. Erste Näherung — der
# Wert lässt sich über die Blockade-Zeitstempel im Eventlog nachschärfen.
VINTED_SOURCE = "vinted"
VINTED_COOLDOWN_SECONDS = 20.0
# Das anonyme Sitzungslimit ist volumenbasiert (~250 Treffer je Bootstrap,
# 1.9.1-Abnahmelauf). Jeder Fallback-Aufruf bootstrappt ohnehin frisch —
# eine blockierte Quelle wird deshalb nicht endgültig beendet, sondern nach
# einer wachsenden Abklingzeit erneut versucht: erster Anlauf nach 60 s
# (öffnete die Quelle im 1.9.2-Abnahmelauf einmal wieder), zweiter nach
# 120 s. Scheitert auch der, endet sie ehrlich mit `blocked`.
VINTED_RETRY_COOLDOWN_SCHEDULE = (60.0, 120.0)
VINTED_BLOCK_RETRY_LIMIT = len(VINTED_RETRY_COOLDOWN_SCHEDULE)
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
    # Additiv seit 1.9.3; None heißt wie bisher: alle Anzeigen, egal wie alt.
    max_age_days: int | None = Field(default=None, ge=1, le=3650)
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
            max_age_days=self.filters.max_age_days,
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


def _derived_key(value: Any, source: str) -> str | None:
    """Gibt die Ursprungsanzeige als listing_key zurück, nicht als nackte ID."""

    text = str(value or "").strip()
    if not text:
        return None
    return text if text.startswith(f"{source}:") else f"{source}:{text}"


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
            # Additiv seit 1.8.0: der Modus trägt die Bedeutung, damit Clients
            # nicht selbst aus drei Feldern schließen müssen.
            "mode": normalize_delivery_mode(
                shipping_available=raw.get("shipping_available"),
                shipping_cost=shipping,
            ),
        },
        "location": {
            "postal_code": raw.get("postal_code"),
            "place": raw.get("place"),
        },
        "offer": {
            "format": offer_format,
            "auction": offer_format == "auction",
            # Additiv seit 1.8.0: gesetzt, wenn diese Zeile aus der
            # Einzelpreisliste eines Konvoluts abgeleitet wurde. Die URL zeigt
            # dann weiterhin auf die Ursprungsanzeige.
            "derived_from": _derived_key(raw.get("derived_from"), source),
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
        # Additiv seit 1.8.0: der Anzeigetext bleibt, die Bedeutung trägt der
        # Code. Vorher leitete erst der Browser per Regex einen Code ab.
        "condition_code": normalize_condition(
            raw.get("condition"), result_info.get("condition")
        ),
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


def _vinted_cooldown_remaining(
    last_at: dict[str, Any], now: float, *, retry_attempt: int = 0
) -> float:
    last = last_at.get(VINTED_SOURCE)
    if last is None:
        return 0.0
    if retry_attempt > 0:
        index = min(retry_attempt, len(VINTED_RETRY_COOLDOWN_SCHEDULE)) - 1
        window = VINTED_RETRY_COOLDOWN_SCHEDULE[index]
    else:
        window = VINTED_COOLDOWN_SECONDS
    try:
        return max(0.0, window - (now - float(last)))
    except (TypeError, ValueError):
        return 0.0


def _advance_state(
    state: dict[str, Any],
    request: V2BatchRequest,
    *,
    page_complete: bool,
    next_page: int | None,
    failed: bool,
    degraded: bool,
    listings: int,
    now: float | None = None,
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

    search_index = int(updated.get("search_index") or 0)
    current = request.searches[search_index]
    sources = list(current.sources)
    source_index = int(updated.get("source_index") or 0)
    source = sources[source_index] if source_index < len(sources) else None

    # Seit 1.8.5 rotieren die Quellen: nach jeder verarbeiteten Seite ist die
    # nächste noch offene Quelle an der Reihe. Dafür braucht jede Quelle einen
    # eigenen Seitenzeiger, sonst könnte die Rotation nicht dort weitermachen,
    # wo die Quelle stehen geblieben ist. Ältere Fortsetzungstoken tragen die
    # Felder nicht und starten deshalb mit leeren Vorgaben.
    cursors = dict(updated.get("source_pages") or {})
    done = list(updated.get("sources_done") or [])

    if page_complete or next_page is None:
        if source is not None and source not in done:
            done.append(source)
            updated["sources_complete"] = int(updated.get("sources_complete") or 0) + 1
        cursors.pop(source, None)
    elif source is not None:
        cursors[source] = next_page

    updated["source_pages"] = cursors
    updated["sources_done"] = done

    # Zeitstempel je Quelle: Grundlage für die Vinted-Abklingzeit. Ältere
    # Fortsetzungstoken tragen das Feld nicht und starten ohne Vorgeschichte.
    now_ts = time.time() if now is None else float(now)
    last_at = dict(updated.get("source_last_at") or {})
    if source is not None:
        last_at[source] = now_ts
    updated["source_last_at"] = last_at
    updated.pop("pacing", None)

    # Ein anstehender Blockade-Retry wartet länger als die normale Schonfrist
    # (Staffel 60 s, 120 s je Anlauf).
    retry_attempt = int(
        (updated.get("source_retry_counts") or {}).get(VINTED_SOURCE) or 0
    )

    next_index = None
    deferred_index = None
    for step in range(1, len(sources) + 1):
        candidate = (source_index + step) % len(sources)
        name = sources[candidate]
        if name in done:
            continue
        if name == VINTED_SOURCE and _vinted_cooldown_remaining(
            last_at, now_ts, retry_attempt=retry_attempt
        ) > 0:
            # Vinted lässt seinen Zug aus, solange die Abklingzeit läuft.
            # Bleibt keine andere Quelle offen, kommt Vinted trotzdem an die
            # Reihe — dann mit Wartehinweis, denn die Taktung gehört dem
            # Browser (1.8.6), nicht einem blockierenden Server.
            if deferred_index is None:
                deferred_index = candidate
            continue
        next_index = candidate
        break
    if next_index is None and deferred_index is not None:
        next_index = deferred_index
        remaining = _vinted_cooldown_remaining(
            last_at, now_ts, retry_attempt=retry_attempt
        )
        if remaining > 0:
            updated["pacing"] = {
                "source": VINTED_SOURCE,
                "wait_ms": int(remaining * 1000),
                "reason": "vinted_access_window",
            }

    if next_index is not None:
        updated["source_index"] = next_index
        updated["page"] = int(cursors.get(sources[next_index], 0))
        return updated, False, False

    search_index += 1
    updated["search_index"] = search_index
    updated["source_index"] = 0
    updated["page"] = 0
    updated["source_pages"] = {}
    updated["sources_done"] = []
    updated["searches_complete"] = int(updated.get("searches_complete") or 0) + 1
    return updated, search_index >= len(request.searches), True


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

    # Wiederaufnahme statt endgültigem `blocked`: Das Vinted-Sitzungslimit ist
    # volumenbasiert, und jeder erneute Aufruf bootstrappt frisch. Eine
    # blockierte Quelle bleibt deshalb begrenzt oft offen und versucht nach
    # der Retry-Abklingzeit dieselbe Seite noch einmal.
    retry_counts = dict(state.get("source_retry_counts") or {})
    if source == VINTED_SOURCE:
        attempts = int(retry_counts.get(VINTED_SOURCE) or 0)
        if (
            source_status["status"] == "blocked"
            and page_complete
            and attempts < VINTED_BLOCK_RETRY_LIMIT
        ):
            retry_counts[VINTED_SOURCE] = attempts + 1
            source_status = {
                **source_status,
                "retry": {
                    "attempt": attempts + 1,
                    "limit": VINTED_BLOCK_RETRY_LIMIT,
                    "cooldown_seconds": VINTED_RETRY_COOLDOWN_SCHEDULE[attempts],
                },
            }
            page_complete = False
            next_page = page
            failed = False  # zählt erst, wenn auch der letzte Anlauf scheitert
        elif source_status["status"] == "ok" and attempts:
            retry_counts.pop(VINTED_SOURCE, None)
    state = {**state, "source_retry_counts": retry_counts}

    updated, batch_complete, search_complete = _advance_state(
        state,
        payload,
        page_complete=page_complete,
        next_page=next_page,
        failed=failed,
        degraded=degraded_packet,
        listings=len(listings),
    )
    pacing = updated.pop("pacing", None)
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
                # Additiv seit 1.9.1: ob DIESE Quelle mit diesem Paket fertig
                # wurde. Ohne das Feld schrieb der Browser jeder mitten im
                # Lauf endenden Quelle den Paket-Stop-Grund
                # `packet_budget_reached` zu — das erfundene
                # „Kleinanzeigen-Paketbudget" aus drei Eventlogs.
                "source_complete": bool(page_complete),
                "listings": listings,
                "sources": {source: source_status},
            }
        ],
        "continuation_token": continuation,
        "deployment": deployment,
    }
    if pacing:
        # Additiv: Wartehinweis, wenn nur noch Vinted offen ist und die
        # Abklingzeit läuft. Der Browser entscheidet über die Pause selbst.
        body["pacing"] = pacing
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
