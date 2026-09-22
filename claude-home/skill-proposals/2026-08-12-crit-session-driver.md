# Skill Proposal: crit-session-driver
Date: 2026-08-12
Source: KTP-1062 crit review — seven rounds, sixteen threads, three lost daemons

## Trigger

Any multi-round crit review an agent drives: presenting work for review, addressing comments,
reopening for the next round. Especially when the review will run over several turns.

## Why it earns a skill

Seven rounds this session. Three daemons died and were misdiagnosed as the user closing the tab. The
review sprawled to seven HTML pages and sixteen threads before the user asked for it to be collapsed
into one page. Several CLI behaviours are non-obvious and one is actively dangerous.

## Scope

Global.

## Draft steps

1. **Launch detached, always.** `nohup crit <target> > /tmp/crit.log 2>&1 &` then `disown`. A plain
   background bash dies when the agent's turn ends. `setsid` does not exist on macOS. Verify with
   `curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>` before telling the user it is up.
2. **Relay the URL verbatim** on its own line, and say explicitly that Finish Review is the click
   that hands comments back.
3. **Read the review file, not the daemon.** `~/.crit/reviews/<id>/review.json`. Dedup by walking
   `replies` — a thread whose last reply is the reviewer's is a follow-up, not a new request.
4. **Reply in bulk, per file.** `crit comment --json` from stdin. It rejects a batch spanning
   separate review files; split it. **Never `crit comment --help`** — it is parsed as a comment body
   and posts one. **Never `--clear`** — it removes every comment.
5. **Do not claim to resolve threads.** There is no `--resolve`. Resolution is the reviewer's click.
   Reply with a closing note instead and say so plainly.
6. **Collapse before it sprawls.** Past three or four pages, move analysis to a `reference/`
   subdirectory outside the scanned folder and leave one action page: what needs the human's hands,
   what needs a one-word answer, what is deferred, what is closed behind a toggle. Archive every
   thread verbatim to markdown first so consolidating costs no reasoning.
7. **Answer in the artifact, not only in the thread.** A reply the user has to hunt for is a reply
   they lose. The user asked "where's my answer" once, which is the signal to keep a running decision
   log inside the reviewed document.
