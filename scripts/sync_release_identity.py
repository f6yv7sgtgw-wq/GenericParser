#!/usr/bin/env python3
"""Trägt die Release-Identität aus der einzigen Quelle in alle Artefakte.

`src/generic_parser/release_identity.py` ist die Quelle. Alle übrigen Stellen
sind abgeleitet und werden hier erzeugt statt von Hand gepflegt. Ein
Versionsbump fasst deshalb genau eine Datei an; danach stellt dieses Skript
den Rest her.

    python scripts/sync_release_identity.py            # schreiben
    python scripts/sync_release_identity.py --check     # nur prüfen (CI)

`--check` endet mit Exit-Code 1, sobald ein Artefakt von der Quelle abweicht,
und benennt die betroffenen Dateien.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "generic_parser" / "release_identity.py"


def load_identity() -> dict[str, str]:
    """Liest die Quelle textuell, damit kein Paketimport nötig ist."""

    text = SOURCE.read_text(encoding="utf-8")
    values = dict(re.findall(r'^([A-Z_]+) = "([^"]*)"$', text, re.M))
    missing = [key for key in ("VERSION", "BUILD_ID", "RELEASE_DATE") if key not in values]
    if missing:
        raise SystemExit(f"release_identity.py fehlt: {', '.join(missing)}")
    return values


def asset_tag(build_id: str) -> str:
    """`gp-164-20260812-1` -> `gp-164` als Cache-/Query-Kennung."""

    parts = build_id.split("-")
    if len(parts) < 2:
        raise SystemExit(f"BUILD_ID hat ein unerwartetes Format: {build_id!r}")
    return f"{parts[0]}-{parts[1]}"


def sub(pattern: str, replacement: str, text: str, *, path: Path, expect: int | None = None) -> str:
    result, count = re.subn(pattern, replacement, text, flags=re.M)
    if count == 0:
        raise SystemExit(f"{path}: Muster nicht gefunden: {pattern}")
    if expect is not None and count != expect:
        raise SystemExit(f"{path}: {count} Treffer für {pattern}, erwartet {expect}")
    return result


def render(identity: dict[str, str]) -> dict[Path, str]:
    """Baut den Sollzustand jeder abgeleiteten Datei."""

    version = identity["VERSION"]
    build_id = identity["BUILD_ID"]
    tag = asset_tag(build_id)
    out: dict[Path, str] = {}

    # VERSION.json trägt zwei build_id: die aktive und die des Rollback-Ziels.
    # Die Verankerung am Zeilenanfang trifft ausschließlich die aktive.
    path = ROOT / "VERSION.json"
    text = path.read_text(encoding="utf-8")
    text = sub(r'^(  "version": )"[^"]*"', rf'\g<1>"{version}"', text, path=path, expect=1)
    text = sub(r'^(  "build_id": )"[^"]*"', rf'\g<1>"{build_id}"', text, path=path, expect=1)
    text = sub(r'^(  "release_date": )"[^"]*"',
               rf'\g<1>"{identity["RELEASE_DATE"]}"', text, path=path, expect=1)
    out[path] = text

    path = ROOT / "cloudflare" / "public" / "release-identity.json"
    text = path.read_text(encoding="utf-8")
    text = sub(r'("version":)"[^"]*"', rf'\g<1>"{version}"', text, path=path, expect=1)
    text = sub(r'("build_id":)"[^"]*"', rf'\g<1>"{build_id}"', text, path=path, expect=1)
    out[path] = text

    path = ROOT / "cloudflare" / "public" / "build-identity-0450.js"
    text = path.read_text(encoding="utf-8")
    text = sub(r"version: '[^']*'", f"version: '{version}'", text, path=path, expect=1)
    text = sub(r"buildId: '[^']*'", f"buildId: '{build_id}'", text, path=path, expect=1)
    out[path] = text

    path = ROOT / "cloudflare" / "public" / "service-worker.js"
    text = path.read_text(encoding="utf-8")
    text = sub(r"const CACHE = 'generic-parser-mobile-[^']*'",
               f"const CACHE = 'generic-parser-mobile-{tag}'", text, path=path, expect=1)
    out[path] = text

    path = ROOT / "cloudflare" / "public" / "app.js"
    text = path.read_text(encoding="utf-8")
    text = sub(r"service-worker\.js\?v=gp-[\w.]+", f"service-worker.js?v={tag}", text, path=path, expect=1)
    out[path] = text

    for html in sorted((ROOT / "cloudflare" / "public").glob("*.html")):
        text = html.read_text(encoding="utf-8")
        if "?v=gp-" not in text:
            continue
        out[html] = re.sub(r"\?v=gp-[\w.]+", f"?v={tag}", text)

    path = ROOT / "pocs" / "ebay-notifications" / "package.json"
    text = path.read_text(encoding="utf-8")
    out[path] = sub(r'^(  "version": )"[^"]*"', rf'\g<1>"{version}"', text, path=path, expect=1)

    path = ROOT / "pocs" / "ebay-notifications" / "src" / "index.js"
    text = path.read_text(encoding="utf-8")
    out[path] = sub(r"version: '[^']*'", f"version: '{version}'", text, path=path, expect=1)

    path = ROOT / "docs" / "openapi-module-v2.json"
    text = path.read_text(encoding="utf-8")
    out[path] = sub(r'^(    "version": )"[^"]*"', rf'\g<1>"{version}"', text, path=path, expect=1)

    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    text = sub(r"^(- \*\*Version:\*\* )`[^`]*`", rf"\g<1>`{version}`", text, path=path, expect=1)
    text = sub(r"^(- \*\*Build:\*\* )`[^`]*`", rf"\g<1>`{build_id}`", text, path=path, expect=1)
    out[path] = text

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur prüfen, nichts schreiben; Exit 1 bei Abweichung")
    args = parser.parse_args()

    identity = load_identity()
    targets = render(identity)

    drifted = [path for path, want in targets.items()
               if path.read_text(encoding="utf-8") != want]

    if args.check:
        if drifted:
            print("Release-Identität weicht ab von "
                  f"{identity['VERSION']} / {identity['BUILD_ID']}:")
            for path in drifted:
                print(f"  - {path.relative_to(ROOT)}")
            print("\nBeheben mit: python scripts/sync_release_identity.py")
            return 1
        print(f"Release-Identität konsistent: {identity['VERSION']} / {identity['BUILD_ID']} "
              f"({len(targets)} Artefakte)")
        return 0

    for path in drifted:
        path.write_text(targets[path], encoding="utf-8")
    if drifted:
        print(f"Aktualisiert auf {identity['VERSION']} / {identity['BUILD_ID']}:")
        for path in drifted:
            print(f"  - {path.relative_to(ROOT)}")
    else:
        print(f"Bereits konsistent: {identity['VERSION']} / {identity['BUILD_ID']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
