#!/usr/bin/env bash
#
# Everything that has to be true before zed-markdoc is released.
#
# ONE COPY: ci.yml runs it on every push and pull request, release.yml runs
# it before anything is published. A second list of steps drifts, and the
# half that drifts is always the one nobody watches.
#
# Zed loads the extension as a WebAssembly component, so `--target
# wasm32-wasip2` is not an extra: it is the only build that proves anything
# about what Zed runs. The crate compiles for the host too, and that tells
# you nothing about the component.
#
# Inputs:
#   $1          the zed-markdoc checkout                default: $PWD
#   STRICT      1 to fail on clippy warnings            default: 1
set -euo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT"
ROOT="$PWD"
STRICT="${STRICT:-1}"
WASM_TARGET="${WASM_TARGET:-wasm32-wasip2}"

group() { echo "::group::$*"; }
endgroup() { echo "::endgroup::"; }
die() { echo "::error::$*" >&2; exit 1; }

[ -f Cargo.toml ] || die "no Cargo.toml in $ROOT — point this at the zed-markdoc checkout"
[ -f extension.toml ] || die "no extension.toml in $ROOT — point this at the zed-markdoc checkout"

failed=""
step() {
  local name="$1"; shift
  group "$name"
  if "$@"; then
    endgroup
  else
    endgroup
    echo "::error::$name failed"
    failed="$failed $name"
  fi
}

step "cargo fmt" cargo fmt --all --check

# Cargo.lock is committed, and has to agree with Cargo.toml: every cargo
# invocation below passes --locked, and finding a stale lockfile out here
# costs a push rather than a release.
lock_is_current() { cargo metadata --locked --format-version 1 >/dev/null; }
step "Cargo.lock is current" lock_is_current

if [ "$STRICT" = "1" ]; then
  clippy() { cargo clippy --locked --all-targets --target "$WASM_TARGET" -- -D warnings; }
else
  clippy() { cargo clippy --locked --all-targets --target "$WASM_TARGET"; }
fi
step "cargo clippy" clippy

# extension.toml is the version Zed shows and resolves; Cargo.toml is the
# version cargo builds. A release where they disagree ships a component
# labelled with a version nobody asked for, and nothing says so until a
# writer reports the wrong version in Zed.
step "extension.toml agrees with Cargo.toml" python3 -I .github/scripts/check_extension_manifest.py

step "cargo build --release" cargo build --locked --release --target "$WASM_TARGET"

# A build that silently emitted something other than a wasm module would
# reach Zed as a file it cannot load at all.
wasm="target/$WASM_TARGET/release/zed_markdoc.wasm"
component_exists() {
  [ -s "$wasm" ] || { echo "$wasm is missing or empty" >&2; return 1; }
  local magic
  magic=$(head -c 4 "$wasm" | od -An -tx1 | tr -d ' \n')
  [ "$magic" = "0061736d" ] || { echo "$wasm is not a wasm module (magic: $magic)" >&2; return 1; }
  ls -lh "$wasm"
}
step "the component was produced" component_exists

# The magic number says "wasm"; Zed asks for more. It loads a component, not
# a core module, and reads its API version from a `zed:api-version` custom
# section before anything else.
step "Zed can load the component" python3 -I .github/scripts/check_wasm_component.py "$wasm"

for s in .github/scripts/*.sh; do
  step "bash -n $(basename "$s")" bash -n "$s"
done

if [ -n "$failed" ]; then
  die "failed:$failed"
fi
echo "==> all checks passed"
