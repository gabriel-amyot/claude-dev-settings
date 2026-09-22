# Skill Proposal: gitlab MR verb discoverability

Date: 2026-09-14
Source: KTP-920 Chevron DOOH
Status: **rewritten 2026-09-14** — the original premise was false. See "What I got wrong".

## What I got wrong

The first version of this proposal claimed `gitlab_skill.py` could not create or merge an MR, and proposed adding `mr-create`, `mr-edit` and `mr-merge`.

That was false. `gitlab_skill.py:1346`:

```python
p.add_argument("--action", required=True,
               choices=["create", "list", "approve", "merge", "auto-merge", "update"])
```

`mr --action create` exists, with `--title`, `--source`, `--target`, `--description-file`. So do `merge` and `update`. The functionality was never missing.

The error came from grepping `add_parser` for subparser names and concluding the capability was absent. The verb lives under `--action`, one level below where I looked.

A second false premise compounded it. I believed Python HTTPS was broken on this machine. Verified since, same host same moment, no CA bundle env vars set:

```
requests.get('https://cicd.prod.datasophia.com')  -> 200
urllib.request.urlopen(same)                      -> CERTIFICATE_VERIFY_FAILED
```

It is stdlib `urllib` that fails. `requests` works. `gitlab_skill.py` uses `requests` (`api_request`, line 373). So `mr --action create` would have worked.

Net cost: a hand-rolled curl path for MR create, retitle and merge that was never needed.

## The real gap, and it is small

Discoverability, not functionality.

- There is no `--help`. `python3 gitlab_skill.py --help` returns `{"error": "Unknown command: --help"}`.
- Read verbs are top-level subcommands (`mr-diff`, `mr-note`, `mr-note-edit`, `mr-note-reply`). Write verbs hide under `mr --action`. The naming implies MR writes do not exist.
- The wiki page for this skill already carries a 2026-09-09 correction killing a stale "no merge action" row. The same class of error recurred five days later. A table that needs a correction every week is the wrong mechanism.

## Trigger

An agent needs to create, retitle or merge a GitLab MR behind IAP and must first work out whether the tooling supports it.

## Scope

Global — `~/.claude/skills/gitlab/gitlab_skill.py` and its wiki page.

## Draft steps

1. Make `--help` and a bare invocation print the real subcommand and action list from argparse. This alone prevents the error; everything below is secondary.
2. Add thin `mr-create` / `mr-merge` aliases that forward to `mr --action ...`, so the write verbs are visible at the same level as the read verbs.
3. Have `mr --action create` print the commit range it ships (`git log origin/<target>..origin/<source>`). A `dev`→`main` MR opened for one commit accumulated nine over three weeks while keeping a title describing one of them.
4. Guard `--action merge` against a `main`/`uat` target on any repo path containing `grp-dac` without an explicit override, matching the existing shipping safeguards.
5. On the wiki page, replace the hand-maintained capability table with a pointer to generated `--help` output. Two stale-row corrections in five days is the evidence for this.

## Note for whoever picks this up

Step 1 is the whole value. Steps 2 through 5 are convenience and safety. If only one thing ships, ship `--help`.
