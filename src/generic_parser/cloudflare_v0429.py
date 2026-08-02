"""GenericParser 0.42.9 standalone Free-plan bootstrap."""
from __future__ import annotations
import importlib, traceback
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .build_identity_v0429 import API_CONTRACT, BUILD_ID, BUILD_REVISION, VERSION
SERVICE_MODULE="generic_parser.search_service_v0429"
WORKER_UNIT="standalone-bootstrap+free-cpu+natural-end+coverage-diagnostics"
app=FastAPI(title=f"GenericParser {VERSION}",version=VERSION,docs_url=None,redoc_url=None)
_service:Any|None=None
_last_error:dict[str,Any]|None=None

def identity(): return {"version":VERSION,"build_id":BUILD_ID,"build_revision":BUILD_REVISION,"api_contract":API_CONTRACT}
def headers(): return {"X-GenericParser-Version":VERSION,"X-GenericParser-Build":BUILD_ID,"X-GenericParser-Commit":str(BUILD_REVISION),"X-GenericParser-Contract":API_CONTRACT,"X-GenericParser-Bootstrap":"coverage-diagnostics"}
def respond(status,body): return JSONResponse(status_code=status,content=body,headers=headers())
def failure(request,status,detail,phase,exc=None):
    body={"detail":detail,"retryable":False,"error_type":type(exc).__name__ if exc else "WorkerError","phase":phase,"ray_id":request.headers.get("cf-ray"),"worker":{**identity(),"worker_unit":WORKER_UNIT}}
    if exc: body["traceback"]="".join(traceback.format_exception(type(exc),exc,exc.__traceback__))[-6000:]
    return respond(status,body)
@app.get("/health")
@app.get("/api/version")
async def version(): return respond(200,{"status":"ok",**identity(),"worker_unit":WORKER_UNIT,"search_ready":True,"service_loaded":_service is not None,"service_module":SERVICE_MODULE,"free_plan_mode":True,"packet_size":7,"reported_total_stop_disabled":True,"natural_end_guard":"empty_or_short_source_page","coverage_diagnostics":True,"last_import_error":_last_error})
def load_service():
    global _service,_last_error
    if _service is not None:return _service
    try:
        service=importlib.import_module(SERVICE_MODULE)
        if getattr(service,"API_CONTRACT",None)!=API_CONTRACT: raise RuntimeError("Search-service contract mismatch")
        _service=service;_last_error=None;return service
    except Exception as exc:
        _last_error={"type":type(exc).__name__,"message":str(exc)};raise
@app.post("/api/search")
async def search(request:Request):
    try:
        body=await request.json();service=load_service();payload=service.SearchRequest.model_validate(body);result=await service.search_page(payload,request)
    except Exception as exc:return failure(request,500,"Arbeitspaket konnte nicht verarbeitet werden.","coverage_diagnostics_packet",exc)
    result["worker"]={**(result.get("worker") or {}),**identity(),"worker_unit":WORKER_UNIT,"free_plan_mode":True}
    return respond(200,result)
@app.exception_handler(Exception)
async def uncaught(request,exc): return failure(request,500,"Unbehandelte Bootstrap-Ausnahme.","standalone_bootstrap",exc)
