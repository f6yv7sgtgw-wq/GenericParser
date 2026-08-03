"""GenericParser 0.43.1 bootstrap with single-source deployment identity."""
from __future__ import annotations
import importlib, platform, sys, traceback
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .build_identity_v0431 import API_CONTRACT, BUILD_ID, SEARCH_MODULE, VERSION, identity

WORKER_UNIT = "single-source-identity-bootstrap+source-next-link"
app = FastAPI(title=f"GenericParser {VERSION}", version=VERSION, docs_url=None, redoc_url=None)
_service: Any | None = None
_last_error: dict[str, Any] | None = None

def runtime_identity(component: str) -> dict[str, Any]:
    return {
        **identity(component),
        "worker_unit": WORKER_UNIT,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "module_name": __name__,
        "loaded_modules": [name for name in ("generic_parser.cloudflare_worker", __name__, SEARCH_MODULE) if name in sys.modules],
    }

def headers() -> dict[str, str]:
    return {
        "X-GenericParser-Version": VERSION,
        "X-GenericParser-Build": BUILD_ID,
        "X-GenericParser-Contract": API_CONTRACT,
        "X-GenericParser-Entrypoint": "cloudflare_worker.Default.fetch",
        "X-GenericParser-Identity-Source": "build_identity_v0431",
    }

def respond(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=headers())

def failure(request: Request, status: int, detail: str, phase: str, exc: Exception | None = None) -> JSONResponse:
    body: dict[str, Any] = {"detail": detail, "retryable": False, "phase": phase, "ray_id": request.headers.get("cf-ray"), "worker": runtime_identity("error")}
    if exc:
        body.update({"error_type": type(exc).__name__, "error_message": str(exc), "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-6000:]})
    return respond(status, body)

@app.get("/health")
@app.get("/api/version")
async def version(request: Request) -> JSONResponse:
    return respond(200, {
        "status": "ok",
        **runtime_identity("version"),
        "search_ready": True,
        "service_loaded": _service is not None,
        "service_module": SEARCH_MODULE,
        "identity_source": "build_identity_v0431",
        "request_path": str(request.url.path),
        "free_plan_mode": True,
        "packet_size": 7,
        "pagination_strategy": "source_html_weiter_link",
        "last_import_error": _last_error,
    })

@app.get("/api/import-status")
async def import_status(request: Request) -> JSONResponse:
    return respond(200, {"status": "ok", **runtime_identity("import-status"), "loaded": _service is not None, "last_error": _last_error, "request_path": str(request.url.path)})

def load_service() -> Any:
    global _service, _last_error
    if _service is not None:
        return _service
    try:
        service = importlib.import_module(SEARCH_MODULE)
        if getattr(service, "API_CONTRACT", None) != API_CONTRACT:
            raise RuntimeError(f"Search-service contract mismatch: {getattr(service, 'API_CONTRACT', None)}")
        _service = service
        _last_error = None
        return service
    except Exception as exc:
        _last_error = {"type": type(exc).__name__, "message": str(exc), "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]}
        raise

@app.post("/api/search")
async def search(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        service = load_service()
        payload = service.SearchRequest.model_validate(body)
        result = await service.search_page(payload, request)
    except Exception as exc:
        return failure(request, 500, "Arbeitspaket konnte nicht verarbeitet werden.", "single_identity_search", exc)
    summary = result.get("summary") or {}
    pagination = result.get("pagination") or {}
    listings = result.get("listings") or []
    fetched = int(summary.get("fetched_listings") or 0)
    visible = int(summary.get("visible_listings") or 0)
    hidden = int(summary.get("hidden_by_filter") or 0)
    unique = int(pagination.get("unique_listings") or 0)
    if not (bool(summary.get("data_consistent")) and fetched == visible + hidden and fetched == unique and visible == len(listings)):
        return failure(request, 500, "Arbeitspaket ist inkonsistent.", "response_consistency")
    result["worker"] = {**(result.get("worker") or {}), **runtime_identity("search-response"), "identity_source": "build_identity_v0431"}
    result["deployment_identity"] = {"version_endpoint_equivalent": runtime_identity("version-equivalent"), "search_endpoint": runtime_identity("search")}
    return respond(200, result)

@app.exception_handler(Exception)
async def uncaught(request: Request, exc: Exception) -> JSONResponse:
    return failure(request, 500, "Unbehandelte Bootstrap-Ausnahme.", "standalone_bootstrap", exc)
