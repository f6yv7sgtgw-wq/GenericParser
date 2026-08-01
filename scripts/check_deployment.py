#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

EXPECTED_VERSION = "0.2.0rc2"


def fetch(base_url: str, path: str, token: str | None = None) -> tuple[str, str]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"User-Agent": "GenericParser-DeploymentCheck/0.2d"}
    if token:
        headers["X-GenericParser-Token"] = token
    try:
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            return response.headers.get("content-type", ""), response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"{url} antwortete mit HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"{url} ist nicht erreichbar: {exc.reason}") from exc


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        print("Aufruf: check_deployment.py https://<worker>.workers.dev", file=sys.stderr)
        return 2
    base_url = sys.argv[1]
    token = os.environ.get("APP_TOKEN") or None
    health_type, health_body = fetch(base_url, "/health", token)
    if "json" not in health_type:
        raise RuntimeError("/health liefert kein JSON")
    health = json.loads(health_body)
    if health.get("status") != "ok" or health.get("version") != EXPECTED_VERSION:
        raise RuntimeError(f"Unerwarteter Health-Status: {health}")
    _, index = fetch(base_url, "/")
    if "GenericParser" not in index or "0.2d" not in index:
        raise RuntimeError("Startseite ist nicht die erwartete 0.2d-Oberfläche")
    _, manifest_body = fetch(base_url, "/manifest.webmanifest")
    if json.loads(manifest_body).get("display") != "standalone":
        raise RuntimeError("PWA-Manifest ist nicht standalone")
    print(f"Deployment OK: {base_url} ({EXPECTED_VERSION})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Deployment-Prüfung fehlgeschlagen: {exc}", file=sys.stderr)
        raise SystemExit(1)
