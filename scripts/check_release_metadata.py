#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA=re.compile(r'^[0-9a-f]{40}$')
class ReleaseError(RuntimeError): pass
def text(path:str)->str:
    p=ROOT/path
    if not p.is_file(): raise ReleaseError(f'Pflichtdatei fehlt: {path}')
    return p.read_text(encoding='utf-8')
def require(path:str,*markers:str)->None:
    s=text(path); missing=[m for m in markers if m not in s]
    if missing: raise ReleaseError(f'{path} fehlen Kennungen: {missing}')
def main()->int:
    m=json.loads(text('VERSION.json')); version=m['version']; build=m['build_id']; contract=m['module_contract']
    if version!='0.45.2' or m['package_version']!=version: raise ReleaseError('Releaseversion ist nicht 0.45.2')
    if m['api_contract']!=contract or contract!='generic-parser-module-v1': raise ReleaseError('Modulvertrag verändert')
    if not build.startswith('gp-0452-'): raise ReleaseError('Build-ID passt nicht zu 0.45.2')
    if tomllib.loads(text('pyproject.toml'))['project']['version']!=version: raise ReleaseError('pyproject-Version inkonsistent')
    require(m['build_identity_source'],version,build,contract)
    require(m['browser_identity_source'],version,build,contract)
    require(m['service_worker_source'],version,build,'build-identity-0452.js')
    release=m['release']
    if release['tag']!='v0.45.2': raise ReleaseError('Release-Tag inkonsistent')
    for key in ['technical_reference_commit','metadata_base_commit']:
        if not SHA.fullmatch(release[key]): raise ReleaseError(f'Ungültiger SHA: {key}')
    api='docs/API_0.45.2.md'; notes='docs/releases/0.45.2.md'
    if release['api_documentation']!=api or release['release_notes']!=notes: raise ReleaseError('Doku-Pfade inkonsistent')
    require(api,version,build,contract,'Cloudflare Workers Free','Evercade','SNES','Bekannte Grenzen','https://developers.cloudflare.com/workers/platform/limits/')
    require(notes,version,build,contract,'Prüfmatrix','Rollback')
    for p in [release['deployment_documentation'],release['release_process'],'README.md','CHANGELOG.md','ROADMAP.md','docs/RELEASE_INDEX.md']: text(p)
    policy=m['documentation_policy']
    for k in ['applies_to_all_following_releases','versioned_api_snapshot_required','complete_function_description_required','known_limitations_required','current_free_worker_limits_required','release_notes_required','github_metadata_required','ci_and_live_evidence_required']:
        if policy.get(k) is not True: raise ReleaseError(f'Dokumentationspolicy fehlt: {k}')
    limits=m['cloudflare_free_limits']
    expected={'requests_per_day':100000,'cpu_ms_per_http_request':10,'memory_mb_per_isolate':128,'subrequests_per_invocation':50,'simultaneous_outgoing_connections':6,'compressed_worker_size_mb':3,'startup_time_seconds':1,'log_kb_per_request':256,'environment_variables_per_worker':64,'environment_variable_size_kb':5}
    for k,v in expected.items():
        if limits.get(k)!=v: raise ReleaseError(f'Cloudflare-Limit inkonsistent: {k}')
    verification=m['verification']
    if verification.get('required_for_confirmed_release') is not True: raise ReleaseError('Pflichtabnahme fehlt')
    for name in ['local_tests','github_release_integrity','cloudflare_deployment','live_contract','live_search_packet']:
        if verification[name]['status'] not in {'pending','passed','failed','blocked'}: raise ReleaseError(f'Ungültiger Verifikationsstatus: {name}')
    suite=m['release_test_suite']; paths=suite['paths']
    required={'tests/test_edge_v0452.py','tests/test_infrastructure_v0451.py','tests/test_module_compat_v0451.py','tests/test_search_service_v0444.py','tests/test_pwa_assets.py','tests/test_deployment_02d.py'}
    if not required.issubset(set(paths)): raise ReleaseError(f'Release-Suite fehlen Pflichtprüfungen: {sorted(required-set(paths))}')
    for p in paths: text(p)
    flows=m['contract_tests']
    require(flows['release_integrity_workflow'],'build_identity_v0452.py','cloudflare_worker.py','scripts/run_release_tests.py')
    require(flows['deployment_workflow'],'scripts/check_deployment.py','--live-search','CLOUDFLARE_ACCOUNT_ID','CLOUDFLARE_API_TOKEN','build-identity-0452.js')
    require('wrangler.jsonc','/api/*','/health','/version','/diagnostics','/search')
    print(json.dumps({'release_metadata':'ok','version':version,'build_id':build,'contract':contract,'status':m['status']},ensure_ascii=False)); return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except (ReleaseError,OSError,ValueError,KeyError,json.JSONDecodeError,tomllib.TOMLDecodeError) as exc:
        print(f'Release-Metadatenprüfung fehlgeschlagen: {exc}',file=sys.stderr); raise SystemExit(1)
