# zed-markdoc

The Zed client for [`markdoc-ls`](https://github.com/markdoc-rs/markdoc-ls),
as the extension **Markdoc**, id `markdoc-ls`. It finds the binary and
tells Zed how to start it. That is the whole extension.

Every feature a writer sees is the server's, which runs the same rules CI
runs, so a change to a rule reaches the editor without the extension being
rebuilt. A client that knew anything about Markdoc would be a third place for
the rules to disagree.

## Install

### 1. `markdoc-ls`

The extension starts the program named `markdoc-ls` from the `PATH` Zed sees
for the project, unless a path is set (see [Settings](#settings)). Download
the binary for your platform, `markdoc-ls-<platform>`, from
[its releases](https://github.com/markdoc-rs/markdoc-ls/releases) — empty
until 0.1.0 is published — check it against the `.sha256` beside it, and
save it in a directory on `PATH` as `markdoc-ls` (`markdoc-ls.exe` on
Windows), or set the path to where you saved it; under its release name, on
`PATH`, Zed does not find it. If your project's own setup installed it, set
the path to the file it installed, or put the file's directory on `PATH` if
the file is named `markdoc-ls`. To build it instead, from a `markdoc-ls`
checkout:

```
cargo install --path .
```

`markdoc-ls` depends on `markdoc` and `markdoc-lint` by path, so both have to
be checked out beside it.

There is no download-from-GitHub fallback: an extension that silently
fetched a different build would be the one way an editor could end up
disagreeing with CI.

### 2. The extension

It is not in Zed's extension registry. Both ways in go through
**Install Dev Extension** (`zed: install dev extension`):

- **From a release — no Rust needed.** Unpack
  `zed-markdoc-<version>.tar.gz` and choose the `zed-markdoc-<version>`
  directory inside it. It holds `extension.toml` and the prebuilt component
  as `extension.wasm`; with no `Cargo.toml` there, Zed compiles nothing and
  loads that component as it is.
- **From a checkout of this repository.** Choose the checkout. Zed compiles
  the crate itself — `cargo build --target wasm32-wasip2`, then it writes
  `extension.wasm` beside `extension.toml` (ignored by git) — so this needs a
  Rust toolchain with the `wasm32-wasip2` target, which Zed adds with
  `rustup` if it is missing.

Either way Zed links to the directory rather than copying it, so leave the
directory where it is.

### 3. Turn on the highlighting

Zed does not ask a language server for semantic tokens until it is told to,
and semantic tokens are the only way `markdoc-ls`'s highlighting reaches Zed.
From [Zed's documentation](https://zed.dev/docs/semantic-tokens):

> Semantic tokens are controlled by the `semantic_tokens` setting. By
> default, semantic tokens are disabled.

The setting takes `"off"` (the default), `"combined"` — "Tree-sitter provides
base highlighting, and semantic tokens overlay additional information." — and
`"full"`, which turns tree-sitter highlighting off for the file. Set it for
Markdown in your `settings.json`:

```json
{
  "languages": {
    "Markdown": {
      "semantic_tokens": "combined"
    }
  }
}
```

Use `"combined"`, not `"full"`. The server colours tags and nothing else, so
under `"full"` the headings, emphasis and code in the rest of the file would
lose their colour. As the documentation notes, "Changing the
`semantic_tokens` mode may require a language server restart to take
effect": run `editor: restart language server`.

The extension cannot turn this on for you. Zed reads `semantic_tokens` from
settings alone, and an extension manifest has no field that contributes a
setting. What an extension *can* ship is semantic-token colour rules, and
only for languages it defines itself; this one defines none — it attaches to
Zed's own Markdown. (Zed v1.27.0: `crates/extension/src/extension_manifest.rs`,
`crates/extension_host/src/extension_host.rs`.)

No colour rules are needed. The server emits seven standard token types —
`operator` for `{%`, `%}`, `/%}` and `=`, `keyword` for control tags such as
`if`, `else` and `partial`, `function` for every other tag name, `property`
for attribute names, `string` for quoted values, `number` for numbers and
booleans, `variable` for `$variables` — and Zed's default rules map each to
the theme style of the same name (`zed: show default semantic token rules`).

## What reaches Zed

Zed uses some of what the server offers by default and some only when a
setting asks. The defaults below are Zed v1.27.0's; every setting named is a
per-language one, set under `"languages": { "Markdown": { … } }`.

| From `markdoc-ls` | In Zed |
|---|---|
| Diagnostics, published on open and on every change. On save, and when a watched file changes on disk, the index is rebuilt and every open file re-checked. | on |
| Completion of tag names, variables, partial paths and anchor ids | on |
| Hover | on |
| Go to definition: from `{% partial file="…" %}` to the file, from a reference to the line of the `{% tag %}` that declares its anchor, usually a heading | on |
| Find references, for partials only: from `{% partial file="…" %}`, or from anywhere inside the partial, to the `{% partial %}` tags that include it | on |
| Linked editing: typing in a paired tag's name edits its partner's too | on — `"linked_edits"` defaults to `true` |
| Semantic tokens: the colouring of tags | `"semantic_tokens": "combined"`, [above](#3-turn-on-the-highlighting) |
| Folding of matched `{% tag %}` … `{% /tag %}` pairs | `"document_folding_ranges": "on"` |
| Document symbols — headings and anchors — for the outline and breadcrumbs | `"document_symbols": "on"` |
| Formatting of the inside of `{% %}` tags, and nothing else | `"formatter": { "language_server": { "name": "markdoc-ls" } }` |

Two of those are trade-offs rather than switches. With
`"document_folding_ranges": "on"` Zed folds by the server's ranges wherever
the server returns any, instead of by its own; the server folds tag pairs
only, not headings. And `"formatter"` defaults to `"auto"`, under which Zed
formats Markdown with Prettier rather than with the language server;
`format_on_save` is `"off"` by default, so that applies when you run
`editor: format`.

## Settings

The server path, for testing a local build without putting it on `PATH`:

```json
{ "lsp": { "markdoc-ls": { "binary": { "path": "/path/to/markdoc-ls" } } } }
```

Only `path` is read: `binary.arguments` and `binary.env` are not passed on,
and the server is started with no arguments. `markdoc-ls` has no settings of
its own — which tags declare and reference anchors is read from the corpus's
`markdoc-lint.toml`. The path is read whenever Zed starts the server, so
after changing it run `editor: restart language server`.

Restarting the server (`editor: restart language server`) and its logs
(`dev: open language server logs`) are built into Zed, so the extension
contributes no commands of its own.

## Files changed on disk

After `initialize`, once it knows the corpus root, `markdoc-ls` registers
`workspace/didChangeWatchedFiles` for `**/markdoc-lint.toml`, `**/*.json` and
`**/*.md`, and Zed honours that registration. A config that changes outside
the editor — a pulled branch, a switched worktree — rebuilds the index
without a restart.

That list used to live in the clients, and the clients disagreed: VS Code's
watched configs through `synchronize.fileEvents`, Zed's had no equivalent,
and after such a change every `{% $variable %}` was being checked against a
list that no longer existed. It lives next to the code that rebuilds the
index now, so both editors watch the same files for the same reason.

## No grammar

The extension ships no tree-sitter grammar and defines no language. It
attaches `markdoc-ls` to Zed's built-in Markdown language, because `.md` is
what the corpus is.

That grammar is a CommonMark grammar with no rule for `{% %}`, so on its own
it reads a tag as Markdown text: emphasis inside an attribute value is styled
as emphasis, and a malformed tag looks no different from a well-formed one.
The colouring that knows what a tag is comes from the server's semantic
tokens, computed by the parser that produces the diagnostics — a tag that
parser does not recognise is not coloured. That is why step 3 matters.

## Why Rust

Zed's extension API is built for `wasm32-wasip2` Rust cdylibs: Zed compiles
and loads extensions as WebAssembly components, and Rust is the language its
extension builder compiles. VS Code is the other way round, which is why
[`vscode-markdoc`](https://github.com/markdoc-rs/vscode-markdoc) is
TypeScript.

## Building and checking

What CI runs (`.github/workflows/ci.yml`):

```
cargo fmt --all --check
cargo clippy --locked --all-targets --target wasm32-wasip2 -- -D warnings
cargo build --locked --release --target wasm32-wasip2
python3 .github/scripts/check_extension_manifest.py
python3 .github/scripts/check_wasm_component.py target/wasm32-wasip2/release/zed_markdoc.wasm
```

The first script checks `extension.toml` parses and carries the same version
as `Cargo.toml`. The second checks the build is a component carrying the
`zed:api-version` section Zed reads before loading anything.

## Releases

Pushing a tag such as `0.2.0` publishes a GitHub release with
`zed-markdoc-<version>.tar.gz` — the installable directory from
[step 2](#2-the-extension), with this README and the licence —
the same component under cargo's name, `zed_markdoc.wasm`, and `SHA256SUMS`.
Nothing is published unless the tag equals the version in `extension.toml`,
that equals the version in `Cargo.toml`, and the component passes the check
above.
Both files carry a build-provenance attestation:

```
gh attestation verify zed-markdoc-<version>.tar.gz --repo markdoc-rs/zed-markdoc
```

## License

MIT.
