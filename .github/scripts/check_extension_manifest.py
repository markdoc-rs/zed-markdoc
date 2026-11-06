#!/usr/bin/env python3
"""Check extension.toml is well-formed and agrees with Cargo.toml.

Zed resolves the extension by the version in `extension.toml`, while cargo
builds the version in `Cargo.toml`. If those disagree, a release ships a wasm
component labelled with a version nobody asked for -- a mismatch that is
invisible until a user reports the wrong extension version in Zed.

Run from the repository root. Exits non-zero, with every problem listed, if
anything is wrong.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REQUIRED_KEYS = ("id", "name", "version", "schema_version")


def main() -> int:
    root = Path(__file__).resolve().parents[2]

    try:
        ext = tomllib.loads((root / "extension.toml").read_text())
        crate = tomllib.loads((root / "Cargo.toml").read_text())["package"]
    except (OSError, tomllib.TOMLDecodeError, KeyError) as exc:
        print(f"error: could not read the manifests: {exc}", file=sys.stderr)
        return 1

    problems = [f"extension.toml is missing `{k}`" for k in REQUIRED_KEYS if k not in ext]

    if ext.get("version") != crate.get("version"):
        problems.append(
            f"version mismatch: extension.toml {ext.get('version')!r} "
            f"!= Cargo.toml {crate.get('version')!r}"
        )

    if not ext.get("language_servers"):
        problems.append("extension.toml declares no [language_servers] entry")

    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    print(f"ok: {ext['id']} {ext['version']} (schema_version {ext['schema_version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
