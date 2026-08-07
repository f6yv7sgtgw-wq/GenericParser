#!/usr/bin/env python3
"""Cross-check current GenericParser release metadata, docs, assets and workflows."""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
VALID_STATUS = {"pending", "passed", "failed", "blocked"}

class ReleaseError(RuntimeError): pass

def fail(message: str) -> None: raise ReleaseError(message)
def text(path: str) -> str:
    target=ROOT/path
    if not target.is_file(): fail(f"Pflichtdatei fehlt: {path}")
    return target.read_text(encoding="utf-8")
def metadata() -> dict[str,Any]:
    value=json.loads(text("VERSION.json"))
    if not isinstance(value,dict): fail("VERSION.json muss ein Objekt sein")
    return value

def require(path: str,*markers: str) -> None:
    source=text(path); missing=[m for m in markers if m not in source]
    if missing: fail(f"{path} fehlen Kennungen: {missing}")
def constant(source: str,name: str) -> str|None:
    m=re.search(rf"^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']",source,re.MULTILINE)
    return m.group(1) if m else None

def check_identity(m: dict[str,Any]) -> None:
    version=m.get("version"); build=m.get("build_id"); contract=m.get("module_contract")
    if not isinstance(version,str) or not SEMVER.fullmatch(version): fail("Ungültige Version")
    if m.get("package_version")!=version: fail("package_version != version")
    if not contract or m.get("api_contract")!=contract: fail("API-/Modulvertrag inkonsistent")
    if not isinstance(build,str) or not build.startswith(f"gp-{version.replace('.','')}-"): fail("Build-ID passt nicht zur Version")
    project=tomllib.loads(text("pyproject.toml"))["project"]
    if project.get("version")!=version: fail("pyproject-Version inkonsistent")
    identity_path=m.get("build_identity_source"); identity=text(identity_path)
    for key,value in {"VERSION":version,"BUILD_ID":build,"API_CONTRACT":contract}.items():
        if constant(identity,key)!=value: fail(f"Buildidentität {key} inkonsistent")
    browser=m.get("browser_identity_source"); require(browser,version,build,contract)
    sw=m.get("service_worker_source"); require(sw,version,build,Path(browser).name)
    for key in ["entrypoint","module_api_source","controller_source","controller_base","module_debug_source","auto_resume_source","auto_resume_reference_source","eventlog_source"]:
        value=m.get(key)
        if not isinstance(value,str) or not (ROOT/value.split(':',1)[0]).is_file(): fail(f"Metadatenpfad fehlt: {key}")

def check_docs(m: dict[str,Any]) -> None:
    version=m["version"]; build=m["build_id"]; contract=m["module_contract"]; release=m.get("release") or {}
    if release.get("tag")!=f"v{version}": fail("Release-Tag inkonsistent")
    for key in ["technical_reference_commit","metadata_base_commit"]:
        if not isinstance(release.get(key),str) or not SHA.fullmatch(release[key]): fail(f"Ungültiger SHA: {key}")
    final=release.get("final_commit")
    if final is not None and (not isinstance(final,str) or not SHA.fullmatch(final)): fail("final_commit ungültig")
    api=f"docs/API_{version}.md"; notes=f"docs/releases/{version}.md"
    if release.get("api_documentation")!=api or release.get("release_notes")!=notes: fail("Versionsgebundene Dokumentationspfade inkonsistent")
    require(api,version,build,contract,"Cloudflare Workers Free","Evercade","SNES","Bekannte Grenzen","https://developers.cloudflare.com/workers/platform/limits/")
    require(notes,version,build,contract,"Prüfmatrix","Rollback")
    require("README.md",version,build,api,notes)
    require("CHANGELOG.md",version,contract)
    require("ROADMAP.md",version,m["stable_reference_version"])
    require("docs/RELEASE_INDEX.md",version,build)
    text(release["deployment_documentation"]); text(release["release_process"])

def check_policy_and_limits(m: dict[str,Any]) -> None:
    p=m.get("documentation_policy") or {}
    required=["applies_to_all_following_releases","versioned_api_snapshot_required","complete_function_description_required","known_limitations_required","current_free_worker_limits_required","release_notes_required","github_metadata_required","ci_and_live_evidence_required"]
    if any(p.get(k) is not True for k in required): fail("Dokumentationspolicy unvollständig")
    limits=m.get("cloudflare_free_limits") or {}
    expected={"requests_per_day":100000,"cpu_ms_per_http_request":10,"memory_mb_per_isolate":128,"subrequests_per_invocation":50,"simultaneous_outgoing_connections":6,"compressed_worker_size_mb":3,"startup_time_seconds":1,"log_kb_per_request":256,"environment_variables_per_worker":64,"environment_variable_size_kb":5}
    for k,v in expected.items():
        if limits.get(k)!=v: fail(f"Cloudflare-Limit inkonsistent: {k}")
    if not str(limits.get("official_limits") or "").startswith("https://developers.cloudflare.com/"): fail("Offizielle Cloudflare-Limit-URL fehlt")

def check_verification_and_tests(m: dict[str,Any]) -> None:
    verification=m.get("verification") or {}
    if verification.get("required_for_confirmed_release") is not True: fail("Pflichtabnahme fehlt")
    names=["local_tests","github_release_integrity","cloudflare_deployment","live_contract","live_search_packet"]
    statuses=[]
    for name in names:
        status=(verification.get(name) or {}).get("status")
        if status not in VALID_STATUS: fail(f"Ungültiger Verifikationsstatus: {name}")
        statuses.append(status)
    if "confirmed" in str(m.get("status") or "") and set(statuses)!={"passed"}: fail("Confirmed release mit offenen Prüfungen")
    suite=m.get("release_test_suite") or {}; paths=suite.get("paths") or []
    if suite.get("runner")!="scripts/run_release_tests.py" or suite.get("network_live_tests_enabled") is not False: fail("Release-Suite inkonsistent")
    required={"tests/test_infrastructure_v0451.py","tests/test_module_compat_v0451.py","tests/test_search_service_v0444.py","tests/test_pwa_assets.py","tests/test_deployment_02d.py"}
    if not required.issubset(set(paths)): fail(f"Release-Suite fehlen Pflichtprüfungen: {sorted(required-set(paths))}")
    for path in paths: text(path)

def check_workflows(m: dict[str,Any]) -> None:
    flows=m.get("contract_tests") or {}
    for key in ["ci_workflow","release_integrity_workflow","deployment_workflow"]: text(flows[key])
    integrity=text(flows["release_integrity_workflow"])
    if "paths:" in integrity or "paths-ignore:" in integrity: fail("Release-Integrität darf keinen Pfadfilter haben")
    require(flows["release_integrity_workflow"],"scripts/check_release_metadata.py","scripts/run_release_tests.py","build_identity_v0451.py","cloudflare_v0451.py")
    require(flows["deployment_workflow"],"scripts/check_deployment.py","--live-search","CLOUDFLARE_ACCOUNT_ID","CLOUDFLARE_API_TOKEN","build-identity-0451.js")

def main() -> int:
    m=metadata()
    if int(m.get("metadata_schema") or 0)<21: fail("metadata_schema muss für 0.45.1 mindestens 21 sein")
    check_identity(m); check_docs(m); check_policy_and_limits(m); check_verification_and_tests(m); check_workflows(m)
    print(json.dumps({"release_metadata":"ok","version":m["version"],"build_id":m["build_id"],"contract":m["module_contract"],"status":m["status"]},ensure_ascii=False)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ReleaseError,OSError,ValueError,KeyError,json.JSONDecodeError,tomllib.TOMLDecodeError) as exc:
        print(f"Release-Metadatenprüfung fehlgeschlagen: {exc}",file=sys.stderr); raise SystemExit(1)
