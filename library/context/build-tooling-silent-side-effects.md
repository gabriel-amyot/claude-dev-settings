# Build Tooling Silent Side Effects: `terraform fmt` Scope Creep and `npm install` Lockfile Races

Two build-tooling traps that apply to any org, any repo. Both produce a change nobody asked for, with no error message.

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

**Source:** session `plain-ibis`, Klever KTP-528 feedback webhook wiring session (2026-09-02).
