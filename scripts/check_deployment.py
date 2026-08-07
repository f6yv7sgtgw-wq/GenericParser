#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

EXPECTED_VERSION = "0.45.2"
EXPECTED_BUILD = "gp-0452-20260807-3"
EXPECTED_CONTRACT = "generic-parser-module-v1"


def call(base_url: str, path: str, *, method: str = "GET", body: dict | None = None,
         token: str | None = None, origin: str | None = None,
         request_headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"User-Agent": "GenericParser-DeploymentCheck/0.45.2-build3", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-GenericParser-Token"] = token
    if origin:
        headers["Origin"] = origin
    if request_headers:
        headers.update(request_headers)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=60) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} für {path}: {payload[:800]}") from exc
    except URLError as exc:
        raise RuntimeError(f"{path} nicht erreichbar: {exc.reason}") from exc


def json_call(*args, **kwargs) -> tuple[dict, dict[str, str]]:
    status, headers, raw = call(*args, **kwargs)
    if status != 200:
        raise RuntimeError(f"HTTP {status}, erwartet 200")
    try:
        return json.loads(raw.decode("utf-8")), headers
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Keine JSON-Antwort: {raw[:300]!r}") from exc


def assert_identity(payload: dict, label: str) -> None:
    if payload.get("version") != EXPECTED_VERSION:
        raise RuntimeError(f"{label} version: {payload.get('version')!r} != {EXPECTED_VERSION!r}")
    if payload.get("build_id") != EXPECTED_BUILD:
        raise RuntimeError(f"{label} build_id: {payload.get('build_id')!r} != {EXPECTED_BUILD!r}")
    contract = payload.get("api_contract") or payload.get("module_contract")
    if contract != EXPECTED_CONTRACT:
        raise RuntimeError(f"{label} contract: {contract!r} != {EXPECTED_CONTRACT!r}")


def assert_cors(headers: dict[str, str], label: str) -> None:
    if headers.get("access-control-allow-origin") != "*":
        raise RuntimeError(f"{label}: Access-Control-Allow-Origin fehlt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--live-search", action="store_true")
    parser.add_argument("--browser-origin", default="https://f6yv7sgtgw-wq.github.io")
    args = parser.parse_args()
    if not args.base_url.startswith("https://"):
        parser.error("base_url muss https:// verwenden")

    token = os.environ.get("APP_TOKEN") or None

    health, health_headers = json_call(args.base_url, "/health", token=token, origin=args.browser_origin)
    if health.get("status") != "ok":
        raise RuntimeError(f"Health nicht ok: {health}")
    assert_identity(health, "/health")
    assert_cors(health_headers, "/health")

    version, version_headers = json_call(args.base_url, "/version", token=token, origin=args.browser_origin)
    assert_identity(version, "/version")
    assert_cors(version_headers, "/version")

    diagnostics, diag_headers = json_call(args.base_url, "/diagnostics", token=token, origin=args.browser_origin)
    assert_identity(diagnostics.get("worker") or {}, "/diagnostics")
    assert_cors(diag_headers, "/diagnostics")
    if (diagnostics.get("checks") or {}).get("startup_model") != "eager-asgi-0450":
        raise RuntimeError("Build 3 verwendet nicht den erwarteten eager 0.45.0 ASGI-Start")

    for path in ("/api/module/search", "/api/search", "/search"):
        status, headers, _ = call(
            args.base_url,
            path,
            method="OPTIONS",
            origin=args.browser_origin,
            request_headers={
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-genericparser-contract,x-request-id",
            },
        )
        if status not in (200, 204):
            raise RuntimeError(f"OPTIONS {path}: HTTP {status}")
        assert_cors(headers, f"OPTIONS {path}")
        methods = headers.get("access-control-allow-methods", "")
        if "POST" not in methods or "OPTIONS" not in methods:
            raise RuntimeError(f"OPTIONS {path}: unvollständige Methoden {methods!r}")

    capabilities, capabilities_headers = json_call(
        args.base_url, "/api/module/v1/capabilities", token=token, origin=args.browser_origin
    )
    if capabilities.get("contract") != EXPECTED_CONTRACT:
        raise RuntimeError(f"Capabilities contract: {capabilities.get('contract')!r}")
    assert_cors(capabilities_headers, "/api/module/v1/capabilities")

    if args.live_search:
        payload = {
            "profile": {
                "profile_id": "deployment-evercade",
                "display_name": "Deployment Evercade",
                "query": "Evercade",
                "include_review": True,
                "include_rejected": True,
            },
            "page": 0,
            "source": "auto",
            "debug": {"enabled": False},
        }
        result, search_headers = json_call(
            args.base_url,
            "/api/module/search",
            method="POST",
            body=payload,
            token=token,
            origin=args.browser_origin,
        )
        assert_cors(search_headers, "POST /api/module/search")
        if result.get("contract") != EXPECTED_CONTRACT:
            raise RuntimeError(f"Modulsuche contract: {result.get('contract')!r}")

    print(f"Deployment OK: {args.base_url} ({EXPECTED_VERSION}, {EXPECTED_BUILD})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Deployment-Prüfung fehlgeschlagen: {exc}", file=sys.stderr)
        raise SystemExit(1)
