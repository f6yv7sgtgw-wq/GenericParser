#!/usr/bin/env python3
"""Run the explicitly versioned current-release regression suite."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    metadata = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    suite = metadata.get("release_test_suite") or {}
    paths = suite.get("paths") or []
    if not isinstance(paths, list) or not paths:
        print("Release-Testliste fehlt in VERSION.json", file=sys.stderr)
        return 2
    invalid = [path for path in paths if not isinstance(path, str) or not (ROOT / path).is_file()]
    if invalid:
        print(f"Ungültige Release-Testpfade: {invalid}", file=sys.stderr)
        return 2
    os.environ["GENERIC_PARSER_LIVE_TEST"] = "0"
    print(
        f"GenericParser {metadata.get('version')} · aktuelle Release-Suite · "
        f"{len(paths)} Testdateien"
    )
    return int(pytest.main(["-q", *paths]))


if __name__ == "__main__":
    raise SystemExit(main())
