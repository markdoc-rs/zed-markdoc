//! The Zed client. It finds `markdoc-ls` and tells Zed how to start it.
//!
//! That is the whole extension, and deliberately so: everything a writer
//! sees -- the diagnostics, the completions, the go-to-definition -- is the
//! server's, which is the same code CI runs. A client that knew anything
//! about Markdoc would be a third place for the rules to disagree.
//!
//! VS Code's client follows the same rule. The one thing it adds is a
//! command that starts a new document from a template, which a language
//! server is never asked for.

use zed_extension_api as zed;

struct MarkdocExtension;

impl zed::Extension for MarkdocExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> zed::Result<zed::Command> {
        // An explicit path wins, so a writer testing a build can point at it
        // without putting it on PATH:
        //
        //   "lsp": { "markdoc-ls": { "binary": { "path": "/path/to/markdoc-ls" } } }
        //
        // VS Code's client has had `markdoc.serverPath` from the start and
        // this did not, which is the kind of asymmetry that turns into "it
        // works in the other editor".
        let configured =
            zed::settings::LspSettings::for_worktree(language_server_id.as_ref(), worktree)
                .ok()
                .and_then(|s| s.binary)
                .and_then(|b| b.path);

        // Otherwise `markdoc-ls` on PATH, which is the normal case. The
        // release binary for the platform -- `markdoc-ls-<platform>`, with a
        // `.sha256` beside it -- has to be saved on PATH as `markdoc-ls`
        // (`markdoc-ls.exe` on Windows), because that is the name looked up;
        // one a project's own setup installed under another name is found
        // through the path setting, not PATH.
        //
        // No download-from-GitHub fallback, which is what most Zed
        // extensions do. Which build a corpus runs is that corpus's pin,
        // not this extension's; an extension that silently fetched a
        // different build would be the one way an editor could end up
        // disagreeing with CI.
        let path = match configured {
            Some(p) => p,
            None => worktree.which("markdoc-ls").ok_or_else(|| {
                "markdoc-ls is not on PATH. Download markdoc-ls-<platform> \
                 from github.com/markdoc-rs/markdoc-ls/releases, check it \
                 against the .sha256 beside it, and save it on PATH as \
                 markdoc-ls (markdoc-ls.exe on Windows), or set \
                 lsp.markdoc-ls.binary.path in your Zed settings to where you \
                 saved it; or build it with `cargo install --path .` from a \
                 markdoc-ls checkout. If your project's own setup installed \
                 it, set that path to the file it installed, or put the \
                 file's directory on PATH if the file is named markdoc-ls."
                    .to_string()
            })?,
        };

        Ok(zed::Command {
            command: path,
            args: Vec::new(),
            env: Default::default(),
        })
    }
}

zed::register_extension!(MarkdocExtension);
