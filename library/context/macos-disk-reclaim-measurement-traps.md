# macOS Disk Reclaim — Measurement Traps

Cross-project knowledge for any `/disk-management` run or ad-hoc disk-space cleanup on macOS.
Learned 2026-09-21 on a machine that started at 100% full on the data volume and ended with 28
GiB free.

---

## 1. `df -h /` does not show free space on modern macOS

On an APFS volume group, `/` is the sealed, read-only System volume. It reports something like:

```
/dev/disk3s1s1   460Gi   9.6Gi   3.7Gi   73%   /
```

That `73%` is meaningless. All user data lives on a separate volume:

```
/dev/disk3s5     460Gi   404Gi   3.7Gi  100%   /System/Volumes/Data
```

The `Avail` column is shared and correct on both lines. `Used` and `Capacity` are not. A tool
that prints only the `/` line reports a healthy 73% while the machine is actually full and apps
are failing to write.

**How to apply:** Any disk check on macOS reads `df -h /System/Volumes/Data`, not `df -h /`.
Reading `/` alone is a false-negative generator. `diskutil info / | grep "Container Free Space"`
gives the same truth from the container side and is a useful cross-check.

The `disk-management` skill's `scripts/scan.sh` has this exact bug: its "before" shot runs
`df -h /`. Fix the script to read `/System/Volumes/Data` before trusting its output again.

## 2. `brew cleanup` understates; `--prune=all` is the effective form

Plain `brew cleanup` leaves stale `portable-ruby` vendor copies under
`/opt/homebrew/Library/Homebrew/vendor/portable-ruby/`. On one machine there were three of them
plus old bottles. `brew cleanup --prune=all` freed **5.2 GB** in one pass, the single biggest win
of that run, larger than any individual cache directory.

`~/Library/Caches/Homebrew` showed only 74 MB in a size-ranked scan, so ranking directories by
size gave no hint brew was worth 5 GB. The reclaimable bytes sat in `/opt/homebrew`, which a
`~/Library/Caches/*` scan never looks at.

**How to apply:** Always run `brew cleanup --prune=all`, not plain `brew cleanup`, and do not use
`~/Library/Caches/Homebrew`'s size to decide whether it is worth running.

## 3. Size the exact deletion target, not its parent, before asking the human to choose

A scan reported `Application Support/Steam` at 23 GiB. Listing `steamapps/common` showed two
games. The question put to the user offered "delete both (22 GiB)" or either title alone,
**without per-title sizes**, because only the parent had been measured. He picked one title, a
reasonable read of an unlabelled pair. The actual split was 21 GiB for the title he kept and
about 1 GiB for the one he approved deleting — the approved deletion recovered about 1 GiB of a
22 GiB opportunity, on a menu that hid the only number that mattered.

**How to apply:** Before any `AskUserQuestion` that offers a choice between deletion targets, run
`du -sh` on each individual target and put the per-item size in the option label. Never let a
parent-folder total stand in for the sizes of the items being offered. This generalizes past disk
cleanup to any "pick which of these to delete/keep/merge" prompt: size what you are actually
asking about, not its container.

## 4. Two large reclaimable paths that live outside `Caches/`

Cache-sweeping `~/Library/Caches/*` never touches either of these, so they survive routine
cleanup and quietly grow:

- **`~/Library/Application Support/Claude/vm_bundles`** — roughly 11 GiB. The Claude Desktop
  local agent-mode VM sandbox (`claudevm.bundle` + `warm`). Regenerable: it re-provisions on the
  next agent-mode use, at the cost of a re-download.
- **`~/Library/Application Support/stremio-server/stremio-cache`** — roughly 7.5 GiB. A pure
  streaming buffer that refills as you watch. Its sibling `stremio-server/downloads/` is real
  user content and a different path — do not confuse the two.

Both are Tier B: reinstallable app data, ask before deleting, state what regenerates.

## 5. Browser data: the two paths that look alike

`~/Library/Caches/Google/` (browser cache) can be cleared with no effect on login sessions.
`~/Library/Application Support/Google/` holds cookies and login state and must not be touched by
a routine cleanup. The same split holds for Edge and Firefox: `Caches/` is safe, `Application
Support/` is not. When a user asks whether a cleanup is safe for their browser sessions, name
both paths explicitly — "I cleared Caches, not Application Support" is the answer that actually
resolves the worry.

**Source:** interactive `/disk-management` run on Gabriel's Mac, 2026-09-21.
