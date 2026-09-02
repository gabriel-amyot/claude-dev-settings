# Build Tooling Silent Side Effects

Tooling traps that apply to any org, any repo. Each produces a change, a deletion, or a false
result nobody asked for, with no error message.

---

## `terraform fmt` on an Already-Dirty File Reformats Lines You Never Touched

A terraform file can carry pre-existing `terraform fmt` complaints on the trunk branch. Running `terraform fmt` "to clean up" after an edit reformats every misaligned line in the file, not just the lines the change touched. That buries the real diff and violates any no-opportunistic-changes rule.

**The mechanism:** `terraform fmt` aligns `=` signs within contiguous runs of assignment lines. A comment line breaks a run. Inserting a new comment plus a new key in the middle of an aligned block splits the run, so the keys above the insertion point get newly flagged for realignment even though nobody touched them.

**The discipline:** position new lines so the change introduces zero new fmt deltas, then prove it.

```bash
A=$(mktemp -d); B=$(mktemp -d)
git -C <repo> show origin/<trunk>:<path> > "$A/f.tf"
cp <worktree>/<path> "$B/f.tf"
terraform fmt -check -diff "$A" > "$A/out.txt" 2>&1 || true
terraform fmt -check -diff "$B" > "$B/out.txt" 2>&1 || true
diff <(grep '^-  ' "$A/out.txt" | sort) <(grep '^-  ' "$B/out.txt" | sort)
```

An empty diff means the change added no new complaints. Fix a split-run problem by inserting the new block at a point that is already a run boundary (right after an existing comment-delimited entry), and write the new line at its own natural single-space width, rather than running `fmt` on the whole file.

**How to apply:** Before running `terraform fmt` on any file, check whether the file already carries fmt complaints on trunk (`terraform fmt -check -diff` against the trunk copy). If it does, use the isolated-diff technique above instead of running `fmt` directly.

---

## A Concurrent Background `npm install` Silently Reverts a Manual Lockfile Version Bump

Bumping `package.json` and `package-lock.json` by hand while an `npm install` runs in the background loses the lockfile edit. The install started before the edit, reads the old `package.json`, and rewrites `package-lock.json` back to the old version. No error, no warning.

**The tell:** `git diff --stat` shows `package.json` changed but `package-lock.json` unchanged, right after a bump that should have touched both.

**The fix, in order:**
1. Bump `package.json`.
2. Run `npm install --package-lock-only`.
3. Verify the lockfile is actually in the diff.

Never hand-edit a lockfile's version field. Never bump `package.json` while an `npm install` is running in the background against the same working tree.

**How to apply:** After any version bump touching `package.json`, confirm `package-lock.json` shows a matching diff before committing. If it does not, check for a background install and rerun `npm install --package-lock-only`.

---

**Source (above two sections):** session `plain-ibis`, Klever KTP-528 feedback webhook wiring session (2026-09-02).

---

## `git worktree remove --force` Silently Deletes Gitignored Local Files (`.env.local`, Tokens, Service Accounts)

`git status` ignores gitignored files by design. A worktree reporting `dirty=0` can still hold a `.env.local`, `.env`, `*.token`, `*.secret`, or `terraform/.service-account` file. It looks clean and safe to delete.

`git worktree remove --force` deletes the whole directory, gitignored files included. There is no warning and no recovery.

Real numbers from a run that surfaced this: 36 worktrees across two repos, 25 removed. Six held a gitignored `.env.local`. Three of those six were on the removal list. Two of the three differed from the main checkout. One differed by 4 lines, the only copy of a dev Slack webhook value. The other differed by 2 lines.

This intersects any org rule against modifying or deleting `.env.local`. A bulk worktree removal is the path that breaks that rule without anyone naming the file. The rule guards the file by name. This command deletes it by directory.

**How to apply:** Before any bulk worktree removal, scan each worktree for gitignored secret files. Back up every hit, plus the main checkout's copy for a diff, to a dated folder outside any repo, before removing anything:

```bash
find "$WT" -maxdepth 2 \
  \( -name '.env.local' -o -name '.env' -o -name '*.token' \
     -o -name '*.secret' -o -name '.service-account' \) \
  -not -path '*/node_modules/*'
```

---

## A Failed Probe Reports Absence, Not "Could Not Check" — a Shared Pattern

The first draft of a worktree secret scan read:

```bash
HITS=$(ls -1 "$WT"/.env.local "$WT"/*.token "$WT"/*.secret 2>/dev/null | wc -l)
```

Under zsh, a glob matching nothing is a hard error (`no matches found`). That error killed the command before `ls` ever ran. `2>/dev/null` hid the error text. `HITS` came back `0` for every worktree, and the scan reported "no local secret files in any worktree" while a `.env.local` sat in six of them.

**A negative result is trustworthy only if the scan is known to run.** Prove the tool works before trusting a "not found." Check a case known to be positive first, or use `find`, which does its own matching and does not depend on shell globbing.

This is the same failure family as two `promotion-image-preflight.sh` false-RED causes documented in the Klever wiki (`documentation/bibliotheque/stack/ci-cd/gitlab-ci-patterns.md`): a zip-artifact FaaS repo with no Docker image by design, and an expired `gcloud` auth token. All three cases share one shape. An empty or RED result meant the check errored. It did not mean the target item was missing.

**How to apply:** When a scan or gate returns a suspiciously clean or suspiciously uniform negative across every input, verify the tool ran before trusting the negative. Test it against one known-positive case first.

---

**Source (above two sections):** session `plain-ibis`, Klever post-close worktree cleanup (2026-09-02).
