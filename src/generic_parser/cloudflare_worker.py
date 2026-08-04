"""Cloudflare-Python-Worker entrypoint for GenericParser 0.44.6.4.

Version and recovery-probe requests are answered directly by this lightweight
entrypoint. ASGI, FastAPI and the reference search chain are imported only for
``POST /api/search``. The package ``__init__`` is never executed by the live
Worker path.
"""
from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import json
import sys
import types
from pathlib import Path
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

_MODULE_DIR = Path(__file__).resolve().parent
_APP = None
_ASGI = None
_BOOTSTRAP_ERROR = None


def _load_identity_module():
    name = "_generic_parser_build_identity_v04464"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, _MODULE_DIR / "build_identity_v04464.py")
    if spec is None or spec.loader is None:
        raise ImportError("build identity could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_ID = _load_identity_module()


def _headers() -> dict[str, str]:
    return {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "x-genericparser-version": _ID.VERSION,
        "x-genericparser-build": _ID.BUILD_ID,
        "x-genericparser-contract": _ID.API_CONTRACT,
        "x-genericparser-bootstrap": "direct-light-probe+lazy-asgi",
    }


def _json_response(body, status: int = 200) -> Response:
    return Response(
        json.dumps(body, ensure_ascii=False, separators=(",", ":")),
        status=status,
        headers=_headers(),
    )


def _header(request, name: str):
    try:
        return request.headers[name]
    except Exception:
        return None


def _identity() -> dict[str, object]:
    return {
        "version": _ID.VERSION,
        "build_id": _ID.BUILD_ID,
        "api_contract": _ID.API_CONTRACT,
        "entrypoint": _ID.ENTRYPOINT,
        "bootstrap_module": _ID.BOOTSTRAP_MODULE,
        "search_module": _ID.SEARCH_MODULE,
        "worker_unit": _ID.WORKER_UNIT,
        "reference_version": _ID.FUNCTIONAL_REFERENCE,
        "runtime_reference": _ID.RUNTIME_REFERENCE,
        "recovery_reference": _ID.RECOVERY_REFERENCE,
        "technical_base": _ID.TECHNICAL_BASE,
    }


def _version_body() -> dict[str, object]:
    return {
        "status": "ok",
        **_identity(),
        "bootstrap_ready": True,
        "search_ready": True,
        "service_loaded": _APP is not None,
        "lazy_search_import": True,
        "lazy_asgi_import": True,
        "package_init_executed": False,
        "packet_size": 7,
        "pause_ms": 5000,
        "pagination_strategy": "source_html_weiter_link",
        "functional_reference": _ID.FUNCTIONAL_REFERENCE,
        "traffic_light_model": "v2-active-rules",
        "empty_fields_ignored": True,
        "functional_rollback": True,
        "experimental_0445_runtime": False,
        "diagnostic_mode": "reference_optional",
        "coverage_schema_required": False,
        "coverage_schema": None,
        "html_503_classification": "temporary_upstream_or_cloudflare_response",
        "controller_recovery": {
            "enabled": True,
            "mode": "staged-saved-state-auto-resume-light-probe",
            "triggers": [
                "cloudflare_1101",
                "cloudflare_1102",
                "retry_exhausted_after_repeated_html_503",
            ],
            "probe_endpoint": "/api/recovery-probe",
            "probe_mode": "bootstrap_lazy",
            "probe_imports_search_service": False,
            "backoff_ms": [90000, 180000, 360000],
            "jitter_ratio": 0.10,
            "probe_intervals_ms": [30000, 60000, 120000],
            "max_probe_attempts": 3,
            "max_auto_resumes": 2,
            "classify_headers": ["cf-error-type", "cf-error-origin", "retry-after", "cf-ray"],
            "search_core_changed": False,
        },
        "last_bootstrap_error": _BOOTSTRAP_ERROR,
    }


def _probe_body(request) -> dict[str, object]:
    checks = {
        "entrypoint_ready": True,
        "identity_consistent": bool(_ID.VERSION and _ID.BUILD_ID and _ID.API_CONTRACT),
        "lazy_asgi_loader_ready": callable(_load_asgi_app),
        "reference_core_declared": _ID.FUNCTIONAL_REFERENCE == "0.44.4",
        "package_init_skipped": True,
    }
    return {
        "status": "ready" if all(checks.values()) else "not_ready",
        **_identity(),
        "bootstrap_ready": all(checks.values()),
        "search_ready": all(checks.values()),
        "lazy_search_import": True,
        "lazy_asgi_import": True,
        "service_loaded": _APP is not None,
        "reference_core_loaded": False,
        "reference_core_declared": True,
        "probe_mode": "bootstrap_lazy",
        "probe_imports_search_service": False,
        "checks": checks,
        "probe_duration_ms": 0,
        "retryable": False,
        "ray_id": _header(request, "cf-ray"),
        "last_bootstrap_error": _BOOTSTRAP_ERROR,
    }


def _ensure_lightweight_package() -> types.ModuleType:
    package_name = "generic_parser"
    existing = sys.modules.get(package_name)
    if existing is not None:
        if not getattr(existing, "__path__", None):
            existing.__path__ = [str(_MODULE_DIR)]
        return existing

    package = types.ModuleType(package_name)
    package.__file__ = str(_MODULE_DIR / "__init__.py")
    package.__package__ = package_name
    package.__path__ = [str(_MODULE_DIR)]
    package.__gp_init_executed__ = False
    spec = importlib.machinery.ModuleSpec(package_name, loader=None, is_package=True)
    spec.submodule_search_locations = [str(_MODULE_DIR)]
    package.__spec__ = spec
    sys.modules[package_name] = package
    return package


def _load_asgi_app():
    global _APP, _ASGI, _BOOTSTRAP_ERROR
    if _APP is not None and _ASGI is not None:
        return _ASGI, _APP
    try:
        _ensure_lightweight_package()
        asgi_module = importlib.import_module("asgi")
        bootstrap = importlib.import_module(_ID.BOOTSTRAP_MODULE)
        app = getattr(bootstrap, "app")
        _ASGI = asgi_module
        _APP = app
        _BOOTSTRAP_ERROR = None
        return _ASGI, _APP
    except Exception as exc:
        _BOOTSTRAP_ERROR = {
            "type": type(exc).__name__,
            "message": str(exc).replace("\n", " ")[:500],
        }
        sys.modules.pop(_ID.BOOTSTRAP_MODULE, None)
        raise


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(str(request.url)).path
        method = str(request.method).upper()

        if method == "OPTIONS":
            return Response(
                "",
                status=204,
                headers={
                    **_headers(),
                    "access-control-allow-origin": "*",
                    "access-control-allow-methods": "GET,POST,OPTIONS",
                    "access-control-allow-headers": "content-type,x-genericparser-token,x-genericparser-recovery-probe",
                },
            )

        if method == "GET" and path in {"/health", "/api/version"}:
            return _json_response(_version_body(), 200)

        if method == "GET" and path == "/api/recovery-probe":
            body = _probe_body(request)
            return _json_response(body, 200 if body["bootstrap_ready"] else 503)

        if method != "POST" or path != "/api/search":
            return _json_response({"detail": "Not found", "worker": _identity()}, 404)

        try:
            asgi_module, app = _load_asgi_app()
        except Exception as exc:
            return _json_response(
                {
                    "detail": "ASGI-Suchpfad konnte noch nicht geladen werden. Der Suchstand bleibt erhalten.",
                    "retryable": True,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc).replace("\n", " ")[:500],
                    "phase": "lazy_asgi_bootstrap_import",
                    "ray_id": _header(request, "cf-ray"),
                    "worker": _identity(),
                    "bootstrap": {"mode": "direct-light-probe+lazy-asgi", "package_init_executed": False},
                },
                503,
            )

        return await asgi_module.fetch(app, request, self.env)
