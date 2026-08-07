#!/usr/bin/env python3
"""Validate deployed GenericParser 0.45.1, CORS and one optional live packet."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
def metadata()->dict[str,Any]: return json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8'))

def request(base,path,*,method='GET',payload=None,token=None,origin='https://f6yv7sgtgw-wq.github.io',timeout=60):
    url=urljoin(base.rstrip('/')+'/',path.lstrip('/')); headers={'Accept':'application/json','User-Agent':'GenericParser-DeploymentCheck/0.45.1','Origin':origin}
    if payload is not None: headers['Content-Type']='application/json'
    if token: headers['X-GenericParser-Token']=token
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
        if headers.get(k)!=v: raise RuntimeError(f'Header {k} stimmt nicht')

def check(base,release,live=False):
    h,b=obj(request(base,'/health')); identity(h,b,release)
    h,b=obj(request(base,'/version')); identity(h,b,release)
    _,diag=obj(request(base,'/diagnostics'))
    if diag.get('status')!='ok' or not (diag.get('checks') or {}).get('cors'): raise RuntimeError('Diagnostics/CORS nicht OK')
    status,h,_=request(base,'/api/module/search',method='OPTIONS')
    if status not in (200,204): raise RuntimeError(f'Preflight HTTP {status}')
    if h.get('access-control-allow-origin') not in ('*','https://f6yv7sgtgw-wq.github.io'): raise RuntimeError('CORS Origin fehlt')
    if 'POST' not in h.get('access-control-allow-methods',''): raise RuntimeError('CORS POST fehlt')
    index_status,_,index=request(base,'/')
    if index_status!=200 or release['version'] not in index or release['build_id'] not in index: raise RuntimeError('Browser-Assetstand stimmt nicht')
    sw_status,_,sw=request(base,'/service-worker.js')
    if sw_status!=200 or release['build_id'] not in sw or Path(release['browser_identity_source']).name not in sw: raise RuntimeError('Service Worker nicht aktuell')
    live_summary=None
    if live:
        payload={'profile':{'profile_id':'deployment:live','display_name':'Deployment live packet','query':os.getenv('CLOUDFLARE_LIVE_QUERY','Evercade'),'include_review':True,'include_rejected':True},'page':0,'source':'auto','debug':{'enabled':False}}
        _,data=obj(request(base,'/api/module/search',method='POST',payload=payload,token=os.getenv('APP_TOKEN') or None))
        listings=data.get('listings') or []
        if len(listings)>7 or data.get('contract')!=release['module_contract']: raise RuntimeError('Live-Paket verletzt Modulvertrag')
        live_summary={'listings':len(listings)}
    return live_summary

def main():
    p=argparse.ArgumentParser(); p.add_argument('base_url'); p.add_argument('--live-search',action='store_true'); a=p.parse_args()
    release=metadata(); summary=check(a.base_url,release,a.live_search)
    print(json.dumps({'deployment':'ok','url':a.base_url,'version':release['version'],'build_id':release['build_id'],'contract':release['module_contract'],'cors':'passed','live_packet':summary},ensure_ascii=False)); return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e: print(f'Deployment-Prüfung fehlgeschlagen: {e}',file=sys.stderr); raise SystemExit(1)
