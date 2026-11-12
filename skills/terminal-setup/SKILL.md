---
name: terminal-setup
description: Manage this user's macOS terminal environment — Ghostty config, Starship prompt, Claude Code statusline, zsh aliases/functions, modern CLI tools, and the cheat-sheet. Use whenever they want to add/remove/change a shell alias or function, a Ghostty keybind or setting, the prompt or statusline, the color theme/font, or install/wire a new CLI tool. Keeps everything consistent (Dracula palette) and the cheat-sheet in sync.
---

# Terminal Setup Manager

This skill manages a curated macOS terminal stack. The setup is **Dracula-themed**
throughout and uses **JetBrainsMono Nerd Font**. When you change anything user-facing,
keep the theme consistent and update the cheat-sheet.

## File inventory (the source of truth)

| What | Path |
|---|---|
| Ghostty config (theme, font, keybinds, window) | `~/.config/ghostty/config` |
| Starship prompt | `~/.config/starship.toml` |
| Claude Code statusline (Layout C "Quota Watch") | `~/.claude/statusline.sh` |
| Claude Code settings (registers statusline) | `~/.claude/settings.json` |
| zsh config (aliases, functions, tool inits) | `~/.zshrc` |
| Cheat-sheet shown by the `cheat` command | `~/.config/cheatsheet.md` |
| Git config (delta diffs) | `~/.gitconfig` |

Installed CLI tools (via Homebrew): `starship zsh-autosuggestions zsh-syntax-highlighting
fzf zoxide eza bat ripgrep fd btop git-delta tlrc jq`. Font: `font-jetbrains-mono-nerd-font`.

## Dracula palette (use these hex codes for any new color)

```
bg #282a36   current-line #44475a   comment #6272a4   fg #f8f8f2
cyan #8be9fd  green #50fa7b  orange #ffb86c  pink #ff79c6
purple #bd93f9  red #ff5555  yellow #f1fa8c
```

## Conventions — follow these

- **Always keep `~/.config/cheatsheet.md` in sync.** Any new user-facing alias,
  function, Ghostty keybind, or tool MUST be added to the cheat-sheet (the user
  runs `cheat` to recall everything). This is the most important rule.
- **`~/.zshrc` ordering matters:** completion (`compinit`) → `starship init` →
  `zsh-autosuggestions` → tool inits (fzf, zoxide) → aliases/functions →
  **`zsh-syntax-highlighting` MUST stay the very last sourced line.**
- **Never alias `go`** (it's the Go compiler) — use `gco` for git checkout.
- Don't shadow tools that are still wanted; prefer new alias names over overrides
  unless the override is a clear, reversible upgrade (e.g. `top`→btop, `cat`→bat).
- Homebrew is at `/opt/homebrew`. Plugin sources live in `/opt/homebrew/share/...`.

## How to do common tasks

### Add a shell alias / function
1. Edit `~/.zshrc` (aliases in the "Handy"/"Git" sections; keep syntax-highlighting last).
2. Add a matching line to `~/.config/cheatsheet.md`.
3. Verify: `zsh -i -c 'source ~/.zshrc && alias <name>'` (or `type <fn>`).

### Install + wire a new CLI tool
1. `brew install <tool>`.
2. Add its init/alias/env to `~/.zshrc` (tool-init block for `eval "$(... init)"` style;
   aliases in Handy). Use Dracula colors for any theme option.
3. Add it to the cheat-sheet and to the inventory list above.
4. Verify it loads: `zsh -i -c 'command -v <tool>'`.

### Change Ghostty (keybind, font, theme, window)
1. Edit `~/.config/ghostty/config`.
2. **Validate:** `/Applications/Ghostty.app/Contents/MacOS/ghostty +validate-config --config-file=$HOME/.config/ghostty/config` (expect exit 0).
3. If it's a keybind, add it to the cheat-sheet. Tell the user to reload with
   `Cmd+Shift+,` or restart Ghostty.
4. Browse themes: `ghostty +list-themes`. If the theme changes, re-tint Starship +
   statusline to match.

### Edit the Claude Code statusline
- Script: `~/.claude/statusline.sh`. It reads session JSON on stdin via `jq`.
- Available fields (current schema): `model.{id,display_name}`, `workspace.{current_dir,
  project_dir,git_worktree,repo.{owner,name}}`, `cwd`, `session_id`, `version`,
  `output_style.name`, `cost.{total_cost_usd,total_lines_added,total_lines_removed}`,
  `context_window.{used_percentage,remaining_percentage,context_window_size,
  current_usage.{input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}}`,
  `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}` (Pro/Max only,
  after first response), `effort.level`, `thinking.enabled`.
- Use truecolor escapes with the Dracula palette above.
- **Test:** pipe a sample JSON payload into it, e.g.
  `echo '{"model":{"display_name":"Opus"},"context_window":{"used_percentage":50,"context_window_size":200000}}' | ~/.claude/statusline.sh`

### Change the Starship prompt
- Edit `~/.config/starship.toml`. Powerline segments use `bg:`/`fg:` Dracula colors.
- Optional language/context modules are plain-fg (no bg) to avoid powerline glitches
  when they're absent. `git_metrics` is enabled but can lag in huge repos — disable
  it there if the prompt feels slow.

## After any change
- Shell changes: tell the user to open a new tab or run `reload`.
- Always re-verify (validate command for Ghostty, `zsh -i -c` for shell, sample
  payload for the statusline) before reporting done.
- Confirm the cheat-sheet was updated if anything user-facing changed.
