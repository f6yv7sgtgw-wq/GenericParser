"""GenericParser 0.43.0 standalone Free-plan bootstrap."""
from __future__ import annotations
import importlib, traceback
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .build_identity_v0430 import API_CONTRACT, BUILD_ID, BUILD_REVISION, VERSION

SERVICE_MODULE="generic_parser.search_service_v0430"
WORKER_UNIT="standalone-bootstrap+free-cpu+source-next-link"
app=FastAPI(title=f"GenericParser {VERSION}",version=VERSION,docs_url=None,redoc_url=None)
_service:Any|None=None
_last_error:dict[str,Any]|None=None

def identity(): return {"version":VERSION,"build_id":BUILD_ID,"build_revision":BUILD_REVISION,"api_contract":API_CONTRACT}
def headers(): return {"X-GenericParser-Version":VERSION,"X-GenericParser-Build":BUILD_ID,"X-GenericParser-Commit":str(BUILD_REVISION),"X-GenericParser-Contract":API_CONTRACT,"X-GenericParser-Bootstrap":"source-next-link"}
def respond(status:int,body:dict[str,Any]): return JSONResponse(status_code=status,content=body,headers=headers())
def failure(request:Request,status:int,detail:str,phase:str,exc:Exception|None=None):
    body={"detail":detail,"retryable":False,"error_type":type(exc).__name__ if exc else "WorkerError","phase":phase,"ray_id":request.headers.get("cf-ray"),"worker":{**identity(),"worker_unit":WORKER_UNIT}}
    if exc: body["traceback"]="".join(traceback.format_exception(type(exc),exc,exc.__traceback__))[-6000:]
    return respond(status,body)

@app.get("/health")
@app.get("/api/version")
async def version():
    return respond(200,{"status":"ok",**identity(),"worker_unit":WORKER_UNIT,"search_ready":True,"service_loaded":_service is not None,"service_module":SERVICE_MODULE,"free_plan_mode":True,"packet_size":7,"reported_total_stop_disabled":True,"pagination_strategy":"source_html_weiter_link","last_import_error":_last_error})

@app.get("/api/import-status")
async def import_status(): return respond(200,{"status":"ok",**identity(),"module":SERVICE_MODULE,"loaded":_service is not None,"last_error":_last_error})

def load_service():
    global _service,_last_error
    if _service is not None:return _service
    try:
        service=importlib.import_module(SERVICE_MODULE)
        if getattr(service,"API_CONTRACT",None)!=API_CONTRACT: raise RuntimeError("Search-service contract mismatch")
        _service=service;_last_error=None;return service
    except Exception as exc:
        _last_error={"type":type(exc).__name__,"message":str(exc),"traceback":"".join(traceback.format_exception(type(exc),exc,exc.__traceback__))[-4000:]};raise

@app.post("/api/search")
async def search(request:Request):
    try:
        body=await request.json();service=load_service();payload=service.SearchRequest.model_validate(body);result=await service.search_page(payload,request)
    except Exception as exc:return failure(request,500,"Arbeitspaket konnte nicht verarbeitet werden.","source_next_link_packet",exc)
    summary=result.get("summary") or {};pagination=result.get("pagination") or {};listings=result.get("listings") or []
    fetched=int(summary.get("fetched_listings") or 0);visible=int(summary.get("visible_listings") or 0);hidden=int(summary.get("hidden_by_filter") or 0);unique=int(pagination.get("unique_listings") or 0)
    if not(bool(summary.get("data_consistent")) and fetched==visible+hidden and fetched==unique and visible==len(listings)): return failure(request,500,"Arbeitspaket ist inkonsistent.","response_consistency")
    result["worker"]={**(result.get("worker") or {}),**identity(),"worker_unit":WORKER_UNIT,"free_plan_mode":True}
    return respond(200,result)

@app.exception_handler(Exception)
async def uncaught(request:Request,exc:Exception): return failure(request,500,"Unbehandelte Bootstrap-Ausnahme.","standalone_bootstrap",exc)
