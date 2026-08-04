"""Direct Cloudflare Python Worker for GenericParser 0.44.5.2.

The live request path avoids importlib, package __init__, ASGI, FastAPI,
Pydantic and httpx. The 0.44.5.2 runtime adds persisted cursor pagination,
complete-card price recovery and explicit coverage diagnostics.
"""
from __future__ import annotations

import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint, fetch as worker_fetch

import worker_runtime_v04452_entry as runtime


def _headers():
    return {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "x-genericparser-version": runtime.VERSION,
        "x-genericparser-build": runtime.BUILD_ID,
        "x-genericparser-contract": runtime.API_CONTRACT,
    }


def _json_response(body, status=200):
    return Response(
        json.dumps(body, ensure_ascii=False, separators=(",", ":")),
        status=status,
        headers=_headers(),
    )


def _header(request, name):
    try:
        return request.headers[name]
    except Exception:
        return None


async def _fetch_html(url):
    response = await worker_fetch(
        url,
        method="GET",
        headers={
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile Safari/604.1",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "de-DE,de;q=0.9",
        },
    )
    status = int(response.status)
    if status in {403, 429}:
        raise runtime.UpstreamError(429, f"Kleinanzeigen blockiert den Abruf ({status})", True)
    if status >= 400:
        raise runtime.UpstreamError(502, f"Kleinanzeigen antwortet mit HTTP {status}", status >= 500)
    return await response.text()


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(str(request.url)).path
        method = str(request.method).upper()

        if method == "OPTIONS":
            return Response("", status=204, headers={
                **_headers(),
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET,POST,OPTIONS",
                "access-control-allow-headers": "content-type,x-genericparser-token",
            })

        if method == "GET" and path in {"/health", "/api/version"}:
            return _json_response({
                "status": "ok",
                **runtime.identity(),
                "search_ready": True,
                "service_loaded": True,
                "packet_size": runtime.PACKET_SIZE,
                "pause_ms": 5000,
                "pagination_strategy": "persisted_source_html_weiter_cursor",
                "functional_reference": "0.44.4",
                "operational_candidate": "0.44.5.2",
                "traffic_light_model": "v2-active-rules",
                "empty_fields_ignored": True,
                "direct_worker": True,
                "robust_title_fallback": True,
                "diagnostic_alignment": True,
                "result_information": True,
                "coverage_schema": "direct-stdlib-cursor-price-diagnostics-v1",
                "link_card_fallback": True,
                "false_empty_page_guard": True,
                "cursor_pagination": True,
                "price_fallback": True,
                "diagnostic_events": True,
                "runtime_imports": {
                    "importlib": False,
                    "asgi": False,
                    "fastapi": False,
                    "pydantic": False,
                    "httpx": False,
                },
            })

        if method != "POST" or path != "/api/search":
            return _json_response({"detail": "Not found", "worker": runtime.identity()}, 404)

        try:
            body = await request.json()
            payload = runtime.SearchPayload(body)
            result = await runtime.search_page(payload, _fetch_html)
            summary = result.get("summary") or {}
            pagination = result.get("pagination") or {}
            listings = result.get("listings") or []
            fetched = int(summary.get("fetched_listings") or 0)
            visible = int(summary.get("visible_listings") or 0)
            hidden = int(summary.get("hidden_by_filter") or 0)
            unique = int(pagination.get("unique_listings") or 0)
            if fetched != visible + hidden or visible != len(listings) or fetched != unique:
                return _json_response({
                    "detail": "Arbeitspaket ist inkonsistent.",
                    "retryable": False,
                    "error_type": "ConsistencyError",
                    "phase": "response_consistency",
                    "ray_id": _header(request, "cf-ray"),
                    "worker": runtime.identity(),
                }, 500)
            return _json_response(result, 200)
        except runtime.PayloadError as exc:
            return _json_response({
                "detail": str(exc),
                "retryable": False,
                "error_type": type(exc).__name__,
                "phase": "payload_validation",
                "ray_id": _header(request, "cf-ray"),
                "worker": runtime.identity(),
            }, 400)
        except runtime.ParserLayoutError as exc:
            return _json_response({
                "detail": exc.detail,
                "retryable": False,
                "error_type": type(exc).__name__,
                "phase": "html_extraction",
                "diagnostics": exc.diagnostics,
                "ray_id": _header(request, "cf-ray"),
                "worker": runtime.identity(),
            }, 502)
        except runtime.UpstreamError as exc:
            return _json_response({
                "detail": exc.detail,
                "retryable": exc.retryable,
                "error_type": type(exc).__name__,
                "phase": "upstream_fetch",
                "ray_id": _header(request, "cf-ray"),
                "worker": runtime.identity(),
            }, exc.status)
        except Exception as exc:
            return _json_response({
                "detail": "Arbeitspaket konnte nicht verarbeitet werden.",
                "retryable": True,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "phase": "direct_worker_runtime",
                "ray_id": _header(request, "cf-ray"),
                "worker": runtime.identity(),
            }, 500)
