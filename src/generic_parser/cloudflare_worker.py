"""Cloudflare-Python-Worker-Einstiegspunkt für GenericParser 0.39."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import asgi
from workers import WorkerEntrypoint


def _load_generic_parser_package():
    package_name = "generic_parser"
    if package_name in sys.modules:
        return sys.modules[package_name]
    module_dir = Path(__file__).resolve().parent
    init_file = module_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(package_name, init_file, submodule_search_locations=[str(module_dir)])
    if spec is None or spec.loader is None:
        raise ImportError("generic_parser package could not be initialized")
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)
    return package


_load_generic_parser_package()

from generic_parser.cloudflare_v039 import app  # noqa: E402


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
