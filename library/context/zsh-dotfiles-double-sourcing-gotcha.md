# zsh Dotfiles: `.zshenv` Sourcing `.zshrc` Causes a Double Run

Cross-project knowledge for diagnosing intermittent-looking shell startup errors on macOS.
Learned 2026-08-03 during a personal dotfiles review.

---

## The pattern

zsh's normal login-shell order is `.zshenv` → `.zprofile` → `.zshrc` → `.zlogin`. A pre-existing
pattern in this user's dotfiles had `.zshenv` end with `source ~/.zshrc`. That line causes
`.zshrc` to run twice. The first run happens early, from inside `.zshenv`, before `.zprofile`'s
`eval "$(/opt/homebrew/bin/brew shellenv)"` adds `/opt/homebrew/bin` to `PATH`. The second run
happens later, in the normal, correct order.

## The symptom

Any `.zshrc` line that shells out to `brew` (for example
`` source $(brew --prefix)/... ``) fails silently with `command not found: brew` on the first
pass, then succeeds on the second. The failure surfaces as console output during
Powerlevel10k's instant-prompt phase, which explicitly warns about exactly this condition. The
output looks intermittent and mysterious if you do not know a double run is happening.

**How to apply:** if a `brew`-dependent `.zshrc` line fails once per shell start with no
obvious pattern, check whether `.zshenv` sources `.zshrc` directly. The real fix removes the
dependency on `brew` being resolvable inside `.zshrc` at all. Hardcode the actual absolute path
(`/opt/homebrew/share/...`) instead of `$(brew --prefix)/...`. This matches what Homebrew's own
install-caveat message already recommends verbatim. Removing the `source ~/.zshrc` line from
`.zshenv` also fixes the symptom, but it changes startup behavior beyond this one case. Prefer
the hardcoded-path fix unless the double sourcing is a problem for other reasons too.
