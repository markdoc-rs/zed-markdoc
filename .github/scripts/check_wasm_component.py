#!/usr/bin/env python3
"""Check the built wasm is something Zed will load as an extension.

Zed reads `extension.wasm` in two steps (v1.27.0,
crates/extension_host/src/wasm_host.rs): `parse_wasm_extension_version`
looks for a custom section named `zed:api-version` -- three big-endian u16s,
major.minor.patch -- and refuses the file without one; then wasmtime compiles
the bytes as a *component*, so a core module is refused too.

Neither is checked by `cargo build` succeeding, and the release archive is
installed without compiling anything: Zed loads its `extension.wasm` as it
is, so the first thing to look at those bytes would otherwise be a writer's
editor. The section is searched for the way Zed's parser searches,
everywhere in the binary, including inside the core module a component
wraps -- which is where `zed_extension_api` puts it.

Usage: check_wasm_component.py <path/to/zed_markdoc.wasm>
Exits non-zero, with every problem listed, if Zed would refuse the file.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAGIC = b"\0asm"
SECTION = "zed:api-version"
COMPONENT_LAYER = 1
# Component-level sections whose payload is itself a wasm binary.
CORE_MODULE_SECTION = 1
COMPONENT_SECTION = 4


def leb128_u32(data: bytes, at: int) -> tuple[int, int]:
    """Decode an unsigned LEB128 at `at`; return (value, offset after it)."""
    value = shift = 0
    while True:
        if at >= len(data):
            raise ValueError("truncated LEB128 integer")
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, at
        shift += 7
        if shift > 28:
            raise ValueError("LEB128 integer longer than a u32")


def custom_sections(data: bytes, name: str, found: list[bytes]) -> int:
    """Collect every custom section called `name`, recursing into nested
    binaries. Returns the layer of `data`: 0 for a core module, 1 for a
    component."""
    if len(data) < 8 or data[:4] != MAGIC:
        raise ValueError("no \\0asm magic number")
    layer = int.from_bytes(data[6:8], "little")
    at = 8
    while at < len(data):
        section_id = data[at]
        size, at = leb128_u32(data, at + 1)
        end = at + size
        if end > len(data):
            raise ValueError(f"section {section_id} runs past the end of the file")
        if section_id == 0:
            name_len, start = leb128_u32(data, at)
            if data[start : start + name_len].decode("utf-8", "replace") == name:
                found.append(data[start + name_len : end])
        elif layer == COMPONENT_LAYER and section_id in (CORE_MODULE_SECTION, COMPONENT_SECTION):
            custom_sections(data[at:end], name, found)
        at = end
    return layer


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_wasm_component.py <path/to/extension.wasm>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        data = path.read_bytes()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    problems = []
    found: list[bytes] = []
    layer = None
    try:
        layer = custom_sections(data, SECTION, found)
    except ValueError as exc:
        problems.append(f"not a well-formed wasm binary: {exc}")

    if layer is not None and layer != COMPONENT_LAYER:
        problems.append(f"a core module (layer {layer}), not a component; Zed loads components")
    if layer is not None and not found:
        problems.append(f"no `{SECTION}` custom section; Zed refuses the extension without one")
    for payload in found:
        if len(payload) != 6:
            problems.append(f"`{SECTION}` is {len(payload)} bytes, not the 6 Zed reads")

    if problems:
        for problem in problems:
            print(f"error: {path}: {problem}", file=sys.stderr)
        return 1

    # Zed keeps the last one it sees; so does this.
    payload = found[-1]
    version = ".".join(str(int.from_bytes(payload[i : i + 2], "big")) for i in (0, 2, 4))
    print(f"ok: {path}: a component, {SECTION} {version}, {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
