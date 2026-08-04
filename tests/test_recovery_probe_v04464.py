from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_identity_is_consistent():
    identity = text("src/generic_parser/build_identity_v04464.py")
    browser = text("cloudflare/public/build-identity-04464.js")
    assert 'VERSION = "0.44.6.4"' in identity
    assert 'BUILD_ID = "gp-04464-20260804-1"' in identity
    assert 'API_CONTRACT = "match-v6.11.5-lazy-bootstrap-recovery"' in identity
    assert "version:'0.44.6.4'" in browser
    assert "buildId:'gp-04464-20260804-1'" in browser
    assert "probeMode:'bootstrap_lazy'" in browser


def test_entrypoint_answers_probe_before_asgi_import():
    source = text("src/generic_parser/cloudflare_worker.py")
    prefix = source.split("class Default", 1)[0]
    assert "from generic_parser.cloudflare_v04464 import app" not in source
    assert "import asgi" not in prefix
    assert "from fastapi" not in source
    assert 'path == "/api/recovery-probe"' in source
    assert "_json_response(_version_body(), 200)" in source
    assert "asgi_module, app = _load_asgi_app()" in source
    assert "return await asgi_module.fetch(app, request, self.env)" in source


def test_package_init_is_not_executed_by_worker():
    source = text("src/generic_parser/cloudflare_worker.py")
    assert "spec.loader.exec_module(package)" not in source
    assert "types.ModuleType(package_name)" in source
    assert "package.__gp_init_executed__ = False" in source
    assert "package.__path__ = [str(_MODULE_DIR)]" in source


def test_recovery_probe_does_not_import_search_service():
    source = text("src/generic_parser/cloudflare_v04464.py")
    section = source.split('@app.get("/api/recovery-probe")', 1)[1].split("def load_service", 1)[0]
    assert "load_service()" not in section
    assert "importlib.import_module" not in section
    assert '"probe_mode": "bootstrap_lazy"' in section
    assert '"probe_imports_search_service": False' in section


def test_search_core_remains_exact_reference_wrapper():
    source = text("src/generic_parser/search_service_v04464.py")
    assert "search_service_v0444 as reference" in source
    assert "await reference.search_page(payload, request)" in source
    assert 'REFERENCE_CORE_MODULE = "generic_parser.search_service_v0444"' in source
    assert "SEARCH_BEHAVIOR_CHANGED = False" in source
    assert "worker_runtime_v0445" not in source


def test_browser_recovery_accepts_light_probe_only():
    source = text("cloudflare/public/auto-resume-04464.js")
    assert "body?.bootstrap_ready === true" in source
    assert "body?.lazy_search_import === true" in source
    assert "body?.probe_mode === 'bootstrap_lazy'" in source
    assert source.count("body?.reference_core_loaded === true") == 1
    assert "const checksOk = body?.status === 'ready' && body?.bootstrap_ready === true" in source
    assert "Worker-Bootstrap ist bereit" in source


def test_ui_uses_04464_assets():
    index = text("cloudflare/public/index.html")
    eventlog = text("cloudflare/public/eventlog.html")
    for asset in ("build-identity-04464.js", "controller-04464.js", "auto-resume-04464.js"):
        assert asset in index
    assert "eventlog-04464.js" in eventlog
    assert "0.44.6.4" in index and "0.44.6.4" in eventlog
    assert "gp-04464-20260804-1" in index and "gp-04464-20260804-1" in eventlog
