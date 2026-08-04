"""Shared metadata for GenericParser 0.44.5.

The live Cloudflare path uses constants from worker_runtime_v0445 directly and
does not import this package module.
"""
VERSION = "0.44.5"
BUILD_ID = "gp-0445-20260804-1"
API_CONTRACT = "match-v6.12-direct-free-worker"
ENTRYPOINT = "src/generic_parser/cloudflare_worker.py:Default.fetch"
RUNTIME_MODULE = "worker_runtime_v0445"
WORKER_UNIT = "direct-worker+stdlib-parser+active-rules"
FUNCTIONAL_REFERENCE = "0.44.4"
