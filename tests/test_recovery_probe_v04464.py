from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_legacy_04464_identity_artifacts_remain_self_consistent():
    """Keep the historical 0.44.6.4 recovery snapshot intact as evidence."""
    identity = text("src/generic_parser/build_identity_v04464.py")
    browser = text("cloudflare/public/build-identity-04464.js")
    assert 'VERSION = "0.44.6.4"' in identity
    assert 'BUILD_ID = "gp-04464-20260804-1"' in identity
    assert 'API_CONTRACT = "match-v6.11.5-lazy-bootstrap-recovery"' in identity
    assert "version:'0.44.6.4'" in browser
    assert "buildId:'gp-04464-20260804-1'" in browser
    assert "probeMode:'bootstrap_lazy'" in browser


def test_active_entrypoint_preserves_edge_cors_and_service_binding_cleanup():
    """Assert current recovery/safety guarantees, not a historical implementation."""
    source = text("src/generic_parser/cloudflare_worker.py")
    assert "class Default(WorkerEntrypoint)" in source
    assert 'str(request.method).upper() == "OPTIONS"' in source or 'str(request.method).upper()=="OPTIONS"' in source
    assert "_preflight_response(request)" in source
    assert 'getattr(self.env, "VINTED_BROWSER", None)' in source or 'getattr(self.env,"VINTED_BROWSER",None)' in source
    assert "set_vinted_browser_binding(binding)" in source
    assert "reset_vinted_browser_binding(token)" in source
    assert "finally:" in source
    assert "return await asgi.fetch(app, request, self.env)" in source or "return await asgi.fetch(app,request,self.env)" in source


def test_active_worker_initializes_generic_parser_package_once():
    """The current Python Worker may execute package init; verify guarded one-time setup."""
    source = text("src/generic_parser/cloudflare_worker.py")
    assert 'package_name = "generic_parser"' in source or 'package_name="generic_parser"' in source
    assert "if package_name in sys.modules" in source
    assert "importlib.util.spec_from_file_location" in source
    assert "sys.modules[package_name] = package" in source or "sys.modules[package_name]=package" in source
    assert "spec.loader.exec_module(package)" in source


def test_historical_recovery_probe_still_does_not_import_search_service():
    """The archived recovery endpoint itself must remain lightweight."""
    source = text("src/generic_parser/cloudflare_v04464.py")
    section = source.split('@app.get("/api/recovery-probe")', 1)[1].split("def load_service", 1)[0]
    assert "load_service()" not in section
    assert "importlib.import_module" not in section
    assert '"probe_mode": "bootstrap_lazy"' in section
    assert '"probe_imports_search_service": False' in section


def test_historical_search_core_remains_exact_reference_wrapper():
    source = text("src/generic_parser/search_service_v04464.py")
    assert "search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert 'REFERENCE_CORE_MODULE = "generic_parser.search_service_v0444"' in source
    assert "SEARCH_BEHAVIOR_CHANGED = False" in source
    assert "worker_runtime_v0445" not in source


def test_historical_browser_recovery_accepts_light_probe_only():
    source = text("cloudflare/public/auto-resume-04464.js")
    assert "body?.bootstrap_ready === true" in source
    assert "body?.lazy_search_import === true" in source
    assert "body?.probe_mode === 'bootstrap_lazy'" in source
    assert source.count("body?.reference_core_loaded === true") == 1
    assert "const checksOk = body?.status === 'ready' && body?.bootstrap_ready === true" in source
    assert "Worker-Bootstrap ist bereit" in source


def test_active_ui_uses_current_version_neutral_asset_chain():
    """Do not pin the active UI to archived 0.44.6.4 filenames or literals."""
    index = text("cloudflare/public/index.html")
    eventlog = text("cloudflare/public/eventlog.html")
    assert "controller-0450.js" in index
    assert "auto-resume-0450.js" in index
    assert "source-colors-110.js" in index
    assert "eventlog-0450.js" in eventlog
    assert "build-identity-04464.js" not in index
    assert "controller-04464.js" not in index
    assert "auto-resume-04464.js" not in index
