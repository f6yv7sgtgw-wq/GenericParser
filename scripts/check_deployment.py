#!/usr/bin/env python3
"""Validate the deployed GenericParser release and optionally one live packet."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class HttpResult:
    status: int
    content_type: str
    headers: dict[str, str]
    body: str
    url: str


def metadata() -> dict[str, Any]:
    return json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))


def request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 45.0,
) -> HttpResult:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {
        "Accept": "application/json",
        "User-Agent": "GenericParser-DeploymentCheck/0.45.0",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-GenericParser-Token"] = token
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    outgoing = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(outgoing, timeout=timeout) as response:
            return HttpResult(
                status=response.status,
                content_type=response.headers.get("content-type", ""),
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read().decode("utf-8"),
                url=url,
            )
    except HTTPError as exc:
        return HttpResult(
            status=exc.code,
            content_type=exc.headers.get("content-type", ""),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=exc.read().decode("utf-8", errors="replace"),
            url=url,
        )
    except URLError as exc:
        raise RuntimeError(f"{url} ist nicht erreichbar: {exc.reason}") from exc


def expect_json(result: HttpResult, status: int) -> dict[str, Any]:
    if result.status != status:
        excerpt = " ".join(result.body.split())[:500]
        raise RuntimeError(
            f"{result.url} antwortete mit HTTP {result.status}, erwartet war {status}: {excerpt}"
        )
    if "json" not in result.content_type.casefold():
        raise RuntimeError(f"{result.url} liefert kein JSON ({result.content_type or 'ohne Content-Type'})")
    try:
        value = json.loads(result.body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{result.url} liefert ungültiges JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{result.url} liefert kein JSON-Objekt")
    return value


def expect_identity(result: HttpResult, body: dict[str, Any], release: dict[str, Any]) -> None:
    expected = {
        "version": release["version"],
        "build_id": release["build_id"],
        "api_contract": release["api_contract"],
        "module_contract": release["module_contract"],
    }
    mismatches = {
        key: {"expected": value, "actual": body.get(key)}
        for key, value in expected.items()
        if body.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"Deployment-Identität stimmt nicht: {mismatches}")
    expected_headers = {
        "x-genericparser-version": release["version"],
        "x-genericparser-build": release["build_id"],
        "x-genericparser-contract": release["api_contract"],
        "x-genericparser-module-contract": release["module_contract"],
    }
    header_mismatches = {
        key: {"expected": value, "actual": result.headers.get(key)}
        for key, value in expected_headers.items()
        if result.headers.get(key) != value
    }
    if header_mismatches:
        raise RuntimeError(f"Deployment-Header stimmen nicht: {header_mismatches}")


def check_static_assets(base_url: str, release: dict[str, Any]) -> None:
    index = request(base_url, "/")
    if index.status != 200:
        raise RuntimeError(f"Startseite antwortete mit HTTP {index.status}")
    for marker in ("GenericParser", release["version"], release["build_id"]):
        if marker not in index.body:
            raise RuntimeError(f"Startseite enthält die aktive Kennung nicht: {marker}")

    manifest = expect_json(request(base_url, "/manifest.webmanifest"), 200)
    if manifest.get("display") != "standalone" or manifest.get("start_url") != "./":
        raise RuntimeError("PWA-Manifest ist nicht der erwartete Standalone-Vertrag")

    service_worker = request(base_url, "/service-worker.js?v=0.450")
    if service_worker.status != 200:
        raise RuntimeError(f"Service Worker antwortete mit HTTP {service_worker.status}")
    for marker in (release["version"], release["build_id"], "build-identity-0450.js"):
        if marker not in service_worker.body:
            raise RuntimeError(f"Service-Worker-Cache enthält die aktive Kennung nicht: {marker}")


def check_module_contract(base_url: str, release: dict[str, Any]) -> None:
    health_result = request(base_url, "/health")
    health = expect_json(health_result, 200)
    expect_identity(health_result, health, release)
    if health.get("status") != "ok" or health.get("packet_size") != 7:
        raise RuntimeError(f"Unerwarteter Health-Status: {health}")

    version_result = request(base_url, "/api/version")
    version = expect_json(version_result, 200)
    expect_identity(version_result, version, release)

    capabilities = expect_json(request(base_url, "/api/module/v1/capabilities"), 200)
    if capabilities.get("contract") != release["module_contract"]:
        raise RuntimeError("Capabilities melden den falschen Modulvertrag")
    if capabilities.get("sources") != ["kleinanzeigen"]:
        raise RuntimeError(f"Unerwartete Quellen: {capabilities.get('sources')}")
    if not {"evercade", "snes-pal"}.issubset(set(capabilities.get("integrations") or [])):
        raise RuntimeError("Capabilities enthalten nicht beide Projektadapter")

    profile = {
        "profile_id": "deployment:evercade",
        "display_name": "Deployment · Evercade",
        "query": "Evercade",
        "required_terms": [],
        "excluded_terms": [],
        "brands": ["Evercade", "Blaze"],
        "max_price": 100,
    }
    validated = expect_json(
        request(
            base_url,
            "/api/module/v1/profile/validate",
            method="POST",
            payload=profile,
        ),
        200,
    )
    if validated.get("valid") is not True or validated.get("reference_request_validated") is not True:
        raise RuntimeError(f"Profilvalidierung fehlgeschlagen: {validated}")
    legacy = validated.get("legacy_payload") or {}
    if "required_terms" in legacy or "excluded_terms" in legacy:
        raise RuntimeError("Leere optionale Regeln wurden an den Referenzvertrag weitergegeben")

    disabled = expect_json(request(base_url, "/api/module/v1/self-test"), 409)
    if disabled.get("tests_enabled") is not False or disabled.get("network_used") is not False:
        raise RuntimeError("Deaktivierter Selbsttest meldet einen falschen Zustand")

    enabled = expect_json(request(base_url, "/api/module/v1/self-test?enabled=true"), 200)
    if enabled.get("ok") is not True or enabled.get("network_used") is not False:
        raise RuntimeError(f"Netzwerkfreier Selbsttest fehlgeschlagen: {enabled}")

    openapi = expect_json(request(base_url, "/openapi.json"), 200)
    paths = set((openapi.get("paths") or {}).keys())
    required_paths = {
        "/api/module/v1/capabilities",
        "/api/module/v1/profile/validate",
        "/api/module/v1/search",
        "/api/module/v1/self-test",
    }
    if not required_paths.issubset(paths):
        raise RuntimeError(f"OpenAPI fehlen Modulpfade: {sorted(required_paths - paths)}")


def check_live_packet(
    base_url: str,
    release: dict[str, Any],
    *,
    token: str | None,
    query: str,
) -> dict[str, Any]:
    payload = {
        "profile": {
            "profile_id": "deployment:live",
            "display_name": "Deployment live packet",
            "query": query,
            "include_review": True,
            "include_rejected": True,
        },
        "page": 0,
        "source": "auto",
        "debug": {"enabled": False},
    }
    result = expect_json(
        request(
            base_url,
            "/api/module/v1/search",
            method="POST",
            payload=payload,
            token=token,
            timeout=60.0,
        ),
        200,
    )
    if result.get("contract") != release["module_contract"]:
        raise RuntimeError("Live-Arbeitspaket meldet den falschen Vertrag")
    listings = result.get("listings") or []
    summary = result.get("summary") or {}
    if len(listings) > 7:
        raise RuntimeError(f"Live-Arbeitspaket überschreitet sieben Karten: {len(listings)}")
    if summary.get("visible") != len(listings):
        raise RuntimeError("Live-Arbeitspaket verletzt visible=listings")
    if summary.get("fetched") != int(summary.get("visible") or 0) + int(summary.get("hidden") or 0):
        raise RuntimeError("Live-Arbeitspaket verletzt fetched=visible+hidden")
    deployment = result.get("deployment") or {}
    if deployment.get("build_id") != release["build_id"]:
        raise RuntimeError("Live-Arbeitspaket stammt nicht aus dem erwarteten Build")
    return {
        "query": query,
        "listings": len(listings),
        "fetched": summary.get("fetched"),
        "next_page": (result.get("pagination") or {}).get("next_page"),
        "complete": (result.get("pagination") or {}).get("complete"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", help="vollständige HTTPS-URL des Workers")
    parser.add_argument(
        "--live-search",
        action="store_true",
        help="zusätzlich ein echtes, auf sieben Karten begrenztes Kleinanzeigen-Paket prüfen",
    )
    parser.add_argument(
        "--query",
        default=os.environ.get("CLOUDFLARE_LIVE_QUERY", "").strip() or "Evercade",
        help="Suchbegriff für --live-search (Standard: Evercade)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.base_url.startswith("https://"):
        raise RuntimeError("Die Worker-URL muss mit https:// beginnen")
    release = metadata()
    check_static_assets(args.base_url, release)
    check_module_contract(args.base_url, release)
    live_summary = None
    if args.live_search:
        live_summary = check_live_packet(
            args.base_url,
            release,
            token=os.environ.get("APP_TOKEN") or None,
            query=args.query.strip(),
        )
    print(
        json.dumps(
            {
                "deployment": "ok",
                "url": args.base_url,
                "version": release["version"],
                "build_id": release["build_id"],
                "contract": release["module_contract"],
                "network_free_contract_checks": "passed",
                "live_packet": live_summary,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Deployment-Prüfung fehlgeschlagen: {exc}", file=sys.stderr)
        raise SystemExit(1)
