"""Versionierte, projektunabhängige Modulschnittstelle für GenericParser 0.45.

Der Vertrag kapselt den bewährten Suchkern hinter stabilen Profil-, Ergebnis-
und Diagnosemodellen. Debugdaten werden ausschließlich erzeugt, wenn sie im
Request ausdrücklich aktiviert wurden.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MODULE_CONTRACT = "generic-parser-module-v1"


class ModuleDebugOptions(BaseModel):
    """Explizit aktivierbare Diagnoseoptionen; standardmäßig vollständig aus."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    include_payload: bool = False
    include_timings: bool = True
    max_events: int = Field(default=50, ge=1, le=200)


class ModuleSearchProfile(BaseModel):
    """Quellenunabhängiges Suchprofil für eingebettete Projekte."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    profile_id: str = "manual"
    display_name: str = "Manuelle Suche"
    query: str = Field(min_length=2, max_length=120)
    required_terms: list[str] = Field(default_factory=list)
    excluded_terms: list[str] = Field(default_factory=list)
    model_patterns: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    max_price: float | None = Field(default=None, gt=0)
    market_value: float | None = Field(default=None, gt=0)
    postal_code: str | None = None
    location_id: int | None = Field(default=None, gt=0)
    radius_km: int | None = Field(default=None, ge=0, le=200)
    accept_bundles: bool = False
    accept_incomplete: bool = False
    include_review: bool = True
    include_rejected: bool = True
    sort_by: Literal["relevance", "date", "price_asc", "price_desc"] = "relevance"

    @field_validator(
        "required_terms",
        "excluded_terms",
        "model_patterns",
        "brands",
        mode="before",
    )
    @classmethod
    def normalize_terms(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            value = value.split(",")
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

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        if value in {None, ""}:
            return None
        if len(value) != 5 or not value.isdigit():
            raise ValueError("postal_code muss eine fünfstellige deutsche PLZ sein")
        return value

    @model_validator(mode="after")
    def validate_location(self) -> "ModuleSearchProfile":
        if self.radius_km is not None and self.location_id is None:
            raise ValueError("radius_km erfordert eine verifizierte location_id")
        if self.postal_code is not None and self.location_id is None:
            raise ValueError("postal_code erfordert eine verifizierte location_id")
        return self

    def to_legacy_payload(self, *, page: int = 0, source: str = "auto") -> dict[str, Any]:
        """Übersetzt das Modulprofil in den unveränderten 0.44.4-Requestvertrag.

        Leere optionale Felder werden bewusst nicht übertragen und damit vom
        Referenzkern nicht ausgewertet.
        """

        payload: dict[str, Any] = {
            "mode": "live",
            "query": self.query,
            "page": page,
            "source": source,
            "accept_bundles": self.accept_bundles,
            "accept_incomplete": self.accept_incomplete,
            "include_review": self.include_review,
            "include_rejected": self.include_rejected,
            "sort_by": self.sort_by,
        }
        optional: dict[str, Any] = {
            "required_terms": self.required_terms,
            "excluded_terms": self.excluded_terms,
            "model_patterns": self.model_patterns,
            "brands": self.brands,
            "max_price": self.max_price,
            "market_value": self.market_value,
            "postal_code": self.postal_code,
            "location_id": self.location_id,
            "radius_km": self.radius_km,
        }
        payload.update(
            {
                key: value
                for key, value in optional.items()
                if value is not None and value != [] and value != ""
            }
        )
        return payload


class ModulePageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ModuleSearchProfile
    page: int = Field(default=0, ge=0, le=499)
    source: str = "auto"
    debug: ModuleDebugOptions = Field(default_factory=ModuleDebugOptions)


class ModuleListing(BaseModel):
    """Stabiles, quellenunabhängiges Ergebnisobjekt."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    url: str
    image_url: str | None = None
    price: float | None = None
    price_raw: str | None = None
    postal_code: str | None = None
    place: str | None = None
    source: str = "kleinanzeigen"
    match: dict[str, Any] = Field(default_factory=dict)
    traffic_light: dict[str, Any] = Field(default_factory=dict)
    result_info: dict[str, Any] = Field(default_factory=dict)


class ModulePagination(BaseModel):
    current_page: int
    next_page: int | None = None
    complete: bool
    source: str
    stop_reason: str | None = None


class ModuleSummary(BaseModel):
    fetched: int
    visible: int
    hidden: int
    unique: int
    reported_total: int | None = None
    traffic_lights: dict[str, int] = Field(default_factory=dict)


class ModuleDebugReport(BaseModel):
    enabled: bool = True
    trace_id: str
    elapsed_ms: float
    events: list[dict[str, Any]] = Field(default_factory=list)
    payload: dict[str, Any] | None = None


class ModulePageResponse(BaseModel):
    contract: str = MODULE_CONTRACT
    profile_id: str
    listings: list[ModuleListing]
    pagination: ModulePagination
    summary: ModuleSummary
    deployment: dict[str, Any] = Field(default_factory=dict)
    debug: ModuleDebugReport | None = None


@dataclass(slots=True)
class DebugTrace:
    """Günstiger No-op-Collector bei deaktiviertem Debugmodus."""

    options: ModuleDebugOptions
    trace_id: str
    _started: float = field(default_factory=perf_counter)
    _events: list[dict[str, Any]] = field(default_factory=list)

    def mark(self, name: str, **data: Any) -> None:
        if not self.options.enabled or len(self._events) >= self.options.max_events:
            return
        event: dict[str, Any] = {"name": name}
        if self.options.include_timings:
            event["at_ms"] = round((perf_counter() - self._started) * 1000, 3)
        event.update(data)
        self._events.append(event)

    def report(self, payload: dict[str, Any] | None = None) -> ModuleDebugReport | None:
        if not self.options.enabled:
            return None
        return ModuleDebugReport(
            trace_id=self.trace_id,
            elapsed_ms=round((perf_counter() - self._started) * 1000, 3),
            events=list(self._events),
            payload=payload if self.options.include_payload else None,
        )


def module_response_from_legacy(
    result: dict[str, Any],
    request: ModulePageRequest,
    trace: DebugTrace,
) -> ModulePageResponse:
    """Normalisiert eine bestätigte 0.44.4-Seitenantwort in Modulvertrag v1."""

    trace.mark("legacy_response_received", listing_count=len(result.get("listings") or []))
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    pagination = result.get("pagination") if isinstance(result.get("pagination"), dict) else {}
    listings: list[ModuleListing] = []
    for raw in result.get("listings") or []:
        listings.append(
            ModuleListing(
                id=str(raw.get("id") or ""),
                title=str(raw.get("title") or ""),
                url=str(raw.get("url") or ""),
                image_url=raw.get("image_url"),
                price=raw.get("price"),
                price_raw=raw.get("price_raw"),
                postal_code=raw.get("postal_code"),
                place=raw.get("place"),
                source="kleinanzeigen",
                match=raw.get("match") if isinstance(raw.get("match"), dict) else {},
                traffic_light=(
                    raw.get("traffic_light")
                    if isinstance(raw.get("traffic_light"), dict)
                    else {}
                ),
                result_info=(
                    raw.get("result_info") if isinstance(raw.get("result_info"), dict) else {}
                ),
            )
        )
    next_page = pagination.get("next_page")
    response = ModulePageResponse(
        profile_id=request.profile.profile_id,
        listings=listings,
        pagination=ModulePagination(
            current_page=request.page,
            next_page=int(next_page) if next_page is not None else None,
            complete=bool(pagination.get("complete") is True or next_page is None),
            source=str(pagination.get("source") or request.source),
            stop_reason=(str(pagination.get("stop_reason")) if pagination.get("stop_reason") else None),
        ),
        summary=ModuleSummary(
            fetched=int(summary.get("fetched_listings") or 0),
            visible=int(summary.get("visible_listings") or len(listings)),
            hidden=int(summary.get("hidden_by_filter") or 0),
            unique=int(pagination.get("unique_listings") or len(listings)),
            reported_total=(
                int(summary["reported_total"])
                if summary.get("reported_total") is not None
                else None
            ),
            traffic_lights={
                str(key): int(value)
                for key, value in (result.get("traffic_light_summary") or {}).items()
            },
        ),
        deployment=(
            result.get("deployment_identity")
            if isinstance(result.get("deployment_identity"), dict)
            else {}
        ),
        debug=trace.report(request.profile.to_legacy_payload(page=request.page, source=request.source)),
    )
    trace.mark("module_response_validated", unique=response.summary.unique)
    if response.debug is not None:
        response.debug = trace.report(
            request.profile.to_legacy_payload(page=request.page, source=request.source)
        )
    return response


def run_contract_self_tests() -> dict[str, Any]:
    """Netzwerkfreier, ausdrücklich aktivierbarer Modul-Selbsttest."""

    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(condition), "detail": detail})

    profile = ModuleSearchProfile(
        profile_id="self-test",
        display_name="Self test",
        query="SNES",
        required_terms=["PAL", "", "PAL"],
        excluded_terms=[],
    )
    payload = profile.to_legacy_payload(page=2, source="auto")
    check("profile_normalization", profile.required_terms == ["PAL"], "Leere und doppelte Begriffe entfernt")
    check("empty_fields_ignored", "excluded_terms" not in payload, "Leere Regeln werden nicht übertragen")
    check("pagination_mapping", payload["page"] == 2, "Seitennummer wird unverändert übertragen")

    fake_request = ModulePageRequest(profile=profile, page=2)
    trace = DebugTrace(ModuleDebugOptions(enabled=True), "self-test")
    fake_result = {
        "listings": [
            {
                "id": "1",
                "title": "SNES PAL Spiel",
                "url": "https://example.invalid/1",
                "price": 25,
                "match": {"decision": "accept"},
                "traffic_light": {"color": "green"},
            }
        ],
        "pagination": {"next_page": 3, "complete": False, "source": "fixture", "unique_listings": 1},
        "summary": {"fetched_listings": 1, "visible_listings": 1, "hidden_by_filter": 0},
        "traffic_light_summary": {"green": 1, "yellow": 0, "red": 0},
        "deployment_identity": {"contract": MODULE_CONTRACT},
    }
    mapped = module_response_from_legacy(fake_result, fake_request, trace)
    check("result_contract", mapped.listings[0].id == "1", "Ergebnisobjekt validiert")
    check("traffic_light_contract", mapped.summary.traffic_lights.get("green") == 1, "Ampelzusammenfassung erhalten")

    return {
        "contract": MODULE_CONTRACT,
        "ok": all(item["ok"] for item in checks),
        "network_used": False,
        "checks": checks,
    }


__all__ = [
    "MODULE_CONTRACT",
    "DebugTrace",
    "ModuleDebugOptions",
    "ModuleListing",
    "ModulePageRequest",
    "ModulePageResponse",
    "ModulePagination",
    "ModuleSearchProfile",
    "ModuleSummary",
    "module_response_from_legacy",
    "run_contract_self_tests",
]
