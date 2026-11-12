# Tribal Knowledge: Ghostty config location & terminal-stack tool provenance

**Source:** ai-workshop session — "point me to the ghostty config, list extensions/plugins/tools" (2026-09-01)

---

## 1. Ghostty has no plugin/extension system

Ghostty is not like VS Code — there is no extension marketplace or plugin loader. All
customization (theme, font, keybinds, window behavior, shell-integration features) lives
in the single config file `~/.config/ghostty/config`. When a user asks for Ghostty
"extensions/plugins," the honest answer is: there aren't any — point them at the config
file and, if relevant, at the surrounding CLI tool stack instead.

## 2. terminal-setup skill's tool inventory has two provenance inaccuracies

`~/.claude/skills/terminal-setup/SKILL.md` lists its installed CLI tools as "via Homebrew"
and includes `jq` in that line. Verified on this machine (2026-09-01):

- `jq` is **not** a Homebrew formula here — `brew list --formula | grep jq` returns nothing.
  The `jq` on PATH resolves to `/usr/bin/jq` (jq-1.7.1-apple), Apple's bundled build.
- `Ghostty.app` itself is **not** a Homebrew cask — `brew list --cask` has no `ghostty`
  entry. It lives at `/Applications/Ghostty.app` (checked via `ghostty --version` → 1.3.1),
  so it was installed by direct download, not `brew install --cask ghostty`.

Anyone using the terminal-setup skill's inventory table as a source of truth (e.g. to
`brew upgrade` everything, or to reason about what a fresh-machine bootstrap script needs
to install) will get this wrong for these two entries. The rest of the brew-formula list
in that skill (starship, zsh-autosuggestions, zsh-syntax-highlighting, fzf, zoxide, eza,
bat, ripgrep, fd, btop, git-delta, tlrc) verified correctly as actual Homebrew formulae.

---

**Curator notes:** Nugget 2 is a concrete, low-effort fix — likely belongs as a direct
correction to `~/.claude/skills/terminal-setup/SKILL.md`'s "Installed CLI tools" line
(split out jq and Ghostty.app as "not brew-managed" rather than lumping them into the
Homebrew list) rather than a promoted wiki page. Nugget 1 is minor context, candidate for
a one-line addition to that same skill's "Change Ghostty" section (or just discarded if
too trivial to be worth a permanent home).
