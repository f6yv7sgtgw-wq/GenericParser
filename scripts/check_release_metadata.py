#!/usr/bin/env python3
"""Cross-check release metadata, documentation and active build identities."""

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


class ReleaseError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ReleaseError(message)


def load_json(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} muss ein JSON-Objekt enthalten")
    return value


def text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        fail(f"Pflichtdatei fehlt: {path}")
    return target.read_text(encoding="utf-8")


def require_contains(path: str, *markers: str) -> None:
    source = text(path)
    missing = [marker for marker in markers if marker not in source]
    if missing:
        fail(f"{path} fehlen Kennungen: {missing}")


def constant(source: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']", source, re.MULTILINE)
    return match.group(1) if match else None


def check_version_and_identity(release: dict[str, Any]) -> None:
    version = release.get("version")
    package_version = release.get("package_version")
    build_id = release.get("build_id")
    contract = release.get("module_contract")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        fail(f"Ungültige Semantic-Version: {version!r}")
    if package_version != version:
        fail("package_version stimmt nicht mit version überein")
    if release.get("api_contract") != contract or not contract:
        fail("api_contract und module_contract müssen identisch und gesetzt sein")
    expected_build_prefix = f"gp-{version.replace('.', '')}-"
    if not isinstance(build_id, str) or not build_id.startswith(expected_build_prefix):
        fail(f"Build-ID {build_id!r} beginnt nicht mit {expected_build_prefix!r}")

    pyproject = tomllib.loads(text("pyproject.toml"))
    if pyproject.get("project", {}).get("version") != version:
        fail("pyproject.toml enthält nicht die aktive Paketversion")

    identity_path = release.get("build_identity_source")
    if not isinstance(identity_path, str):
        fail("build_identity_source fehlt")
    identity = text(identity_path)
    expected_constants = {
        "VERSION": version,
        "BUILD_ID": build_id,
        "API_CONTRACT": contract,
    }
    mismatches = {
        name: {"expected": value, "actual": constant(identity, name)}
        for name, value in expected_constants.items()
        if constant(identity, name) != value
    }
    if mismatches:
        fail(f"Python-Buildidentität stimmt nicht: {mismatches}")

    browser_identity_path = release.get("browser_identity_source")
    if not isinstance(browser_identity_path, str):
        fail("browser_identity_source fehlt")
    require_contains(browser_identity_path, version, build_id, contract)

    service_worker_path = release.get("service_worker_source")
    if not isinstance(service_worker_path, str):
        fail("service_worker_source fehlt")
    require_contains(service_worker_path, version, build_id, Path(browser_identity_path).name)

    for key in (
        "entrypoint",
        "module_api_source",
        "controller_source",
        "controller_base",
        "module_debug_source",
        "auto_resume_source",
        "auto_resume_reference_source",
        "eventlog_source",
    ):
        value = release.get(key)
        if not isinstance(value, str):
            fail(f"{key} fehlt")
        path = value.split(":", 1)[0]
        if not (ROOT / path).is_file():
            fail(f"Metadatenpfad aus {key} existiert nicht: {path}")


def check_release_block(metadata: dict[str, Any]) -> None:
    version = metadata["version"]
    release = metadata.get("release")
    if not isinstance(release, dict):
        fail("VERSION.json.release fehlt")
    if release.get("tag") != f"v{version}":
        fail("Git-Tag in VERSION.json entspricht nicht v<VERSION>")
    if not release.get("name") or not release.get("channel"):
        fail("Release-Name oder Kanal fehlt")
    if not isinstance(release.get("prerelease"), bool):
        fail("release.prerelease muss Boolean sein")
    for key in ("technical_reference_commit", "metadata_base_commit"):
        value = release.get(key)
        if not isinstance(value, str) or not SHA.fullmatch(value):
            fail(f"release.{key} ist kein vollständiger Commit-SHA")
    final_commit = release.get("final_commit")
    if final_commit is not None and (not isinstance(final_commit, str) or not SHA.fullmatch(final_commit)):
        fail("release.final_commit ist weder null noch ein vollständiger Commit-SHA")

    api_path = release.get("api_documentation")
    notes_path = release.get("release_notes")
    deployment_path = release.get("deployment_documentation")
    process_path = release.get("release_process")
    for value in (api_path, notes_path, deployment_path, process_path):
        if not isinstance(value, str):
            fail("Release-Dokumentationspfad fehlt")
        text(value)
    expected_api_path = f"docs/API_{version}.md"
    expected_notes_path = f"docs/releases/{version}.md"
    if api_path != expected_api_path:
        fail(f"API-Snapshot muss {expected_api_path} heißen")
    if notes_path != expected_notes_path:
        fail(f"Release Notes müssen {expected_notes_path} heißen")

    require_contains(
        api_path,
        version,
        metadata["build_id"],
        metadata["module_contract"],
        "Cloudflare Workers Free",
        "Evercade",
        "SNES",
        "Bekannte Grenzen",
        "https://developers.cloudflare.com/workers/platform/limits/",
    )
    require_contains(
        notes_path,
        version,
        metadata["build_id"],
        metadata["module_contract"],
        "Prüfmatrix",
        "Rollback",
    )

    require_contains("README.md", version, metadata["build_id"], api_path, notes_path)
    require_contains("CHANGELOG.md", version, metadata["module_contract"])
    require_contains("ROADMAP.md", version, metadata["stable_reference_version"])
    require_contains("docs/RELEASE_INDEX.md", version, metadata["build_id"])


def check_documentation_policy(metadata: dict[str, Any]) -> None:
    policy = metadata.get("documentation_policy")
    if not isinstance(policy, dict):
        fail("documentation_policy fehlt")
    required_true = (
        "applies_to_all_following_releases",
        "versioned_api_snapshot_required",
        "complete_function_description_required",
        "known_limitations_required",
        "current_free_worker_limits_required",
        "release_notes_required",
        "github_metadata_required",
        "ci_and_live_evidence_required",
    )
    disabled = [key for key in required_true if policy.get(key) is not True]
    if disabled:
        fail(f"Verbindliche Dokumentationsregeln fehlen: {disabled}")
    if policy.get("validation_script") != "scripts/check_release_metadata.py":
        fail("documentation_policy.validation_script zeigt nicht auf diesen Check")


def check_cloudflare_limits(metadata: dict[str, Any]) -> None:
    limits = metadata.get("cloudflare_free_limits")
    if not isinstance(limits, dict):
        fail("cloudflare_free_limits fehlt")
    expected = {
        "requests_per_day": 100000,
        "cpu_ms_per_http_request": 10,
        "memory_mb_per_isolate": 128,
        "subrequests_per_invocation": 50,
        "simultaneous_outgoing_connections": 6,
        "compressed_worker_size_mb": 3,
        "startup_time_seconds": 1,
        "log_kb_per_request": 256,
        "environment_variables_per_worker": 64,
        "environment_variable_size_kb": 5,
    }
    mismatches = {
        key: {"expected": value, "actual": limits.get(key)}
        for key, value in expected.items()
        if limits.get(key) != value
    }
    if mismatches:
        fail(f"Cloudflare-Free-Metadaten stimmen nicht mit dem Release-Stichtag: {mismatches}")
    verified_on = limits.get("verified_on")
    if not isinstance(verified_on, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified_on):
        fail("cloudflare_free_limits.verified_on fehlt oder ist ungültig")
    for key in ("official_limits", "official_pricing", "python_runtime"):
        if not str(limits.get(key) or "").startswith("https://developers.cloudflare.com/"):
            fail(f"cloudflare_free_limits.{key} ist keine offizielle Cloudflare-URL")


def check_verification(metadata: dict[str, Any]) -> None:
    verification = metadata.get("verification")
    if not isinstance(verification, dict) or verification.get("required_for_confirmed_release") is not True:
        fail("verification oder Releasepflicht fehlt")
    check_names = (
        "local_tests",
        "github_release_integrity",
        "cloudflare_deployment",
        "live_contract",
        "live_search_packet",
    )
    statuses: dict[str, str] = {}
    for name in check_names:
        item = verification.get(name)
        if not isinstance(item, dict):
            fail(f"verification.{name} fehlt")
        status = item.get("status")
        if status not in VALID_STATUS:
            fail(f"verification.{name}.status ist ungültig: {status!r}")
        statuses[name] = status
    if "confirmed" in str(metadata.get("status") or "") and set(statuses.values()) != {"passed"}:
        fail("Ein bestätigter Release darf keine offene oder fehlgeschlagene Pflichtprüfung enthalten")
    if metadata.get("live_cloudflare_test") is True and statuses["live_contract"] != "passed":
        fail("live_cloudflare_test=true erfordert eine bestandene live_contract-Prüfung")


def check_release_test_suite(metadata: dict[str, Any]) -> None:
    suite = metadata.get("release_test_suite")
    if not isinstance(suite, dict):
        fail("release_test_suite fehlt")
    if suite.get("runner") != "scripts/run_release_tests.py":
        fail("release_test_suite.runner zeigt nicht auf den verbindlichen Runner")
    text(suite["runner"])
    if suite.get("network_live_tests_enabled") is not False:
        fail("Die aktuelle Release-Suite muss ohne externen Live-Test laufen")
    if suite.get("historical_release_assertions_excluded") is not True:
        fail("Historische, gegenseitig ausschließende Release-Assertions müssen getrennt bleiben")
    paths = suite.get("paths")
    if not isinstance(paths, list) or not paths:
        fail("release_test_suite.paths fehlt")
    if len(paths) != len(set(paths)):
        fail("release_test_suite.paths enthält Duplikate")
    for path in paths:
        if not isinstance(path, str) or not path.startswith("tests/"):
            fail(f"Ungültiger Release-Testpfad: {path!r}")
        text(path)
    required = {
        "tests/test_module_v0450.py",
        "tests/test_search_service_v0444.py",
        "tests/test_pwa_assets.py",
        "tests/test_deployment_02d.py",
    }
    if not required.issubset(set(paths)):
        fail(f"Aktuelle Release-Suite enthält nicht alle Pflichtprüfungen: {sorted(required - set(paths))}")


def check_workflows(metadata: dict[str, Any]) -> None:
    workflows = metadata.get("contract_tests") or {}
    for key in ("ci_workflow", "release_integrity_workflow", "deployment_workflow"):
        value = workflows.get(key)
        if not isinstance(value, str):
            fail(f"contract_tests.{key} fehlt")
        text(value)
    release_integrity = text(workflows["release_integrity_workflow"])
    if "paths:" in release_integrity or "paths-ignore:" in release_integrity:
        fail("Der allgemeine Release-Integritätscheck darf keine Pfadfilter haben")
    require_contains(
        workflows["release_integrity_workflow"],
        "scripts/check_release_metadata.py",
        "scripts/run_release_tests.py",
    )
    require_contains(
        workflows["deployment_workflow"],
        "scripts/check_deployment.py",
        "--live-search",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
    )


def main() -> int:
    metadata = load_json("VERSION.json")
    if int(metadata.get("metadata_schema") or 0) < 20:
        fail("metadata_schema muss ab 0.45.0 mindestens 20 sein")
    check_version_and_identity(metadata)
    check_release_block(metadata)
    check_documentation_policy(metadata)
    check_cloudflare_limits(metadata)
    check_verification(metadata)
    check_release_test_suite(metadata)
    check_workflows(metadata)
    print(
        json.dumps(
            {
                "release_metadata": "ok",
                "version": metadata["version"],
                "build_id": metadata["build_id"],
                "contract": metadata["module_contract"],
                "metadata_schema": metadata["metadata_schema"],
                "status": metadata["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReleaseError, OSError, ValueError, KeyError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"Release-Metadatenprüfung fehlgeschlagen: {exc}", file=sys.stderr)
        raise SystemExit(1)
