#!/usr/bin/env python3
"""Validate deployed GenericParser 0.45.2 edge/CORS contract and an optional live packet."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError,URLError
from urllib.parse import urljoin
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
def metadata()->dict[str,Any]: return json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8'))
def request(base,path,*,method='GET',payload=None,token=None,origin=None,timeout=60,preflight_headers=None):
    url=urljoin(base.rstrip('/')+'/',path.lstrip('/')); headers={'Accept':'application/json','User-Agent':'GenericParser-DeploymentCheck/0.45.2'}
    if origin: headers['Origin']=origin
    if payload is not None: headers['Content-Type']='application/json'
    if token: headers['X-GenericParser-Token']=token
    if preflight_headers:
        headers['Access-Control-Request-Method']='POST'; headers['Access-Control-Request-Headers']=preflight_headers
    data=json.dumps(payload).encode() if payload is not None else None
    req=Request(url,data=data,headers=headers,method=method)
    try:
        with urlopen(req,timeout=timeout) as r: return r.status,{k.lower():v for k,v in r.headers.items()},r.read().decode()
    except HTTPError as e: return e.code,{k.lower():v for k,v in e.headers.items()},e.read().decode(errors='replace')
    except URLError as e: raise RuntimeError(f'{url} nicht erreichbar: {e.reason}') from e
def obj(result,expected=200):
    status,headers,body=result
    if status!=expected: raise RuntimeError(f'HTTP {status}, erwartet {expected}: {body[:300]}')
    try: value=json.loads(body)
    except Exception as e: raise RuntimeError('Ungültiges JSON') from e
    if not isinstance(value,dict): raise RuntimeError('JSON-Antwort ist kein Objekt')
    return headers,value
def identity(headers,body,release):
    for key in ('version','build_id','api_contract','module_contract'):
        if body.get(key)!=release[key]: raise RuntimeError(f'{key}: {body.get(key)!r} != {release[key]!r}')
    expected={'x-genericparser-version':release['version'],'x-genericparser-build':release['build_id'],'x-genericparser-module-contract':release['module_contract']}
    for k,v in expected.items():
        if headers.get(k)!=v: raise RuntimeError(f'Header {k} stimmt nicht: {headers.get(k)!r}')
def check_cors(base,origin):
    for path in ['/api/module/search','/api/search','/search']:
        status,h,_=request(base,path,method='OPTIONS',origin=origin,preflight_headers='content-type,x-genericparser-contract,x-genericparser-token,x-request-id')
        if status not in (200,204): raise RuntimeError(f'Preflight {path} HTTP {status}')
        if h.get('access-control-allow-origin') not in ('*',origin): raise RuntimeError(f'CORS Origin fehlt auf {path}')
        if 'POST' not in h.get('access-control-allow-methods',''): raise RuntimeError(f'CORS POST fehlt auf {path}')
        allowed=h.get('access-control-allow-headers','').lower()
        for name in ['content-type','x-genericparser-contract','x-genericparser-token','x-request-id']:
            if name not in allowed: raise RuntimeError(f'CORS Header {name} fehlt auf {path}')
def check(base,release,live=False,origin='https://f6yv7sgtgw-wq.github.io'):
    h,b=obj(request(base,'/health',origin=origin)); identity(h,b,release)
    if b.get('edge_shell') is not True: raise RuntimeError('0.45.2 Edge-Shell nicht aktiv')
    h,b=obj(request(base,'/version',origin=origin)); identity(h,b,release)
    _,diag=obj(request(base,'/diagnostics',origin=origin))
    checks=diag.get('checks') or {}
    if diag.get('status')!='ok' or not checks.get('cors') or not checks.get('preflight') or not checks.get('edge_runtime'): raise RuntimeError('Edge-Diagnostics nicht OK')
    check_cors(base,origin)
    index_status,_,index=request(base,'/')
    if index_status!=200 or release['version'] not in index or release['build_id'] not in index: raise RuntimeError('Browser-Assetstand stimmt nicht')
    sw_status,_,sw=request(base,'/service-worker.js')
    if sw_status!=200 or release['build_id'] not in sw or Path(release['browser_identity_source']).name not in sw: raise RuntimeError('Service Worker nicht aktuell')
    live_summary=None
    if live:
        payload={'profile':{'profile_id':'deployment:evercade','display_name':'Evercade browser E2E','query':os.getenv('CLOUDFLARE_LIVE_QUERY','Evercade'),'include_review':True,'include_rejected':True},'page':0,'source':'auto','debug':{'enabled':False}}
        headers,data=obj(request(base,'/api/module/search',method='POST',payload=payload,token=os.getenv('APP_TOKEN') or None,origin=origin))
        if headers.get('access-control-allow-origin') not in ('*',origin): raise RuntimeError('POST-Antwort ohne Browser-CORS')
        listings=data.get('listings') or []
        if len(listings)>7 or data.get('contract')!=release['module_contract']: raise RuntimeError('Live-Paket verletzt Modulvertrag')
        live_summary={'listings':len(listings),'request_id':headers.get('x-request-id')}
    return live_summary
def main():
    p=argparse.ArgumentParser(); p.add_argument('base_url'); p.add_argument('--live-search',action='store_true'); p.add_argument('--browser-origin',default='https://f6yv7sgtgw-wq.github.io'); a=p.parse_args()
    release=metadata(); summary=check(a.base_url,release,a.live_search,a.browser_origin)
    print(json.dumps({'deployment':'ok','url':a.base_url,'version':release['version'],'build_id':release['build_id'],'contract':release['module_contract'],'cors':'passed','browser_origin':a.browser_origin,'live_packet':summary},ensure_ascii=False)); return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e: print(f'Deployment-Prüfung fehlgeschlagen: {e}',file=sys.stderr); raise SystemExit(1)
