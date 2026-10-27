The library is worth preserving. The prompt-only retrieval architecture is not: it retrieves topical similarity when the task needs an applicable behavioral rule.

Ranked failures, with hook references to `bibliotheque-recall.sh`:

1. **Design limit: retrieval happens before the relevant intent exists.** Org `ALIASES.md:1665` explicitly describes the missing-repo/workspace-map/dev rule. Yet the agent decided to clone mid-task. Neither better keywords nor embeddings over the original prompt can reliably detect that later decision. This is the highest-impact failure.

2. **One-day bug: one concept can satisfy the “two distinctive tokens” threshold.** Lines 79–85 and 123–137 retain both words and stems, then count their intersection. A shared `patterns` becomes both `patterns` and `pattern`, scoring 2 and passing line 138. Long notes supply more matching opportunities; there is no rarity weighting or negative scope. Thus the advertised threshold does not mean two independent signals.

3. **One-day bugs: pointers are suppressed before consumption and paths are malformed.** Lines 148–151 mark pages fired immediately; lines 115–116 subsequently exclude them. Machine prompts can therefore consume a page’s sole opportunity before human work needs it. Compaction does not reset this state. Line 109 also splits paths on whitespace, breaking deduplication for annotated paths.

   Your absolute-path claim needs correction: `os.path.join(src, "/absolute/path")` preserves the absolute path. It does **not** prepend `src`. Tilde paths and annotations do break resolution: org rows 1093–1096 contain both; row 1279 instead contains an absolute path under another username, whose existence needs validation. Expand `~`, separate annotations from paths, canonicalize, and validate existence before indexing.

4. **Design/data limit: a wikilink disambiguation table is being used as an applicability index.** The report records 189/514 org pages and 87/140 global pages without alias rows. Forty-one aliases target one CI page, increasing its opportunities to win while other pages cannot compete. Only nine org rows have keywords; moreover, lines 135–136 prevent keyword-only matches. Adding keywords alone cannot repair coverage.

5. **One-day bugs: suppression and scoping are crude.** Lines 55–57 suppress every prompt containing “library,” including ordinary software-library work. Line 43 uses string-prefix org detection, accepting sibling names sharing the prefix. Lines 29–34 perform no machine-message filtering. The report’s 513 machine-associated pointers demonstrate substantial wasted injection, although transcript association alone does not prove every notification invoked this exact hook.

There is also a measurement contradiction: report lines 5–8 give 782 pointers across 134 injected human prompts, averaging 5.84. Line 146 caps each invocation at five. Historical versions, multiple invocations, or counting errors must explain that discrepancy. The 2.6% opening rate measures consumption, not correctness or behavioral benefit.

Replace retrieval in this order:

1. **Make action-time contracts primary for operational rules.** Add `PreToolUse` handlers inspecting tool name and arguments: `Bash` command structure for cloning/worktrees/deployment; `Write|Edit` paths for documentation and configuration rules. For cloning, resolve repository identity and mapped destination, then reject a wrong destination with `hookSpecificOutput.permissionDecision: "deny"` and a reason naming the applicable page and required correction. Check the subsequent dev checkout too.

   Merely injecting advice cannot repair an already-selected command: `PreToolUse.additionalContext` accompanies the tool result. Use denial when execution must change; use context for advisory information. These are supported [hook controls](https://code.claude.com/docs/en/hooks#pretooluse-decision-control). Parse command structure, including `git -C`; document that opaque scripts and wrappers remain blind spots.

2. **Give each library page an owned trigger contract.** Store frontmatter containing stable ID, org/repository scope, action/tool predicates, exclusions, priority, one-sentence behavioral consequence, and positive/negative examples. For the clone page: action=`git clone`, scope=Klever repository, predicate=destination differs from workspace map, consequence=use mapped destination and dev checkout. Generate the retrieval manifest and alias table from pages. Reject malformed destinations and unresolved references during generation. Keep prose notes descriptive.

3. **Retain prompt retrieval as a selective discovery channel.** First collapse each word to one normalized lexeme; preserve short technical terms through rarity weighting rather than an expanding whitelist. As an immediate patch, require two distinct normalized terms or an exact, boundary-aware alias match, plus scope compatibility.

   Then evaluate BM25 over alias, trigger and summary fields—starting weights 3/4/1, `k1=1.2`, `b=0.75`. Return at most three pointers within 350 tokens, and calibrate an abstention threshold against held-out relevance judgments. Target ≥80% relevant suggestions before rollout. Embeddings can supply additional paraphrase candidates if they improve that benchmark; they cannot enforce destination or branch predicates. Do not replace everything with vector similarity.

4. **Filter machine envelopes before ranking or state mutation.** Exclude observed task-notification/system-reminder envelopes using anchored structural matches. The documented `UserPromptSubmit` payload provides prompt text, not a dependable human-origin flag; prefer transcript provenance when available, and measure uncertain classifications. Do not globally discard useful machine output from action-time retrieval.

5. **Keep disclosure cheap.** Put only library locations, retrieval instructions and shelving policy in `CLAUDE.md`. Use `SessionStart` for a tiny scope/router message; reset retrieval suppression on compact/resume. Track “suggested” separately from successful reads, with canonical page ID/version and context epoch. `PostToolUse` can record successful reads and refresh manifests after library writes. Offer skills/subagents for requested search or shelving; do not launch an LLM librarian on every prompt or bulk-load either INDEX.

For memory, **choose disabling auto-memory and migrating its eight reported files**. Deduplicate useful entries into scoped library pages, attach trigger contracts, and replace alias references into old memory directories. Set `autoMemoryEnabled: false`; document that confirmed durable corrections go through library shelving. [The settings documentation](https://code.claude.com/docs/en/memory#auto-memory) supports disabling and relocation, not a read-only mode.

A memory-write `PreToolUse` denial can preserve built-in reads and redirect attempted writes, but redirection is an instruction—not guaranteed shelving—and incomplete tool/path coverage permits bypasses. `CLAUDE.md` alone is unenforced. `autoMemoryDirectory` inside the library merely relocates automatic authoring, bypassing library placement and trigger maintenance. The chosen approach’s failure mode is forgotten shelving; disabling also does not prohibit an explicitly requested filesystem write.

Measure on held-out sessions and action replays:

- Relevant pointers per injection, injected tokens per human task, and machine-associated injection rate.
- Successful canonical-page reads before the applicable action, including delayed reads and subagent reads.
- Clone destination/branch compliance, repeated violations, and false-positive denials.
- Memory-write attempts, completed library shelving, and new pages with valid triggers.
- Invalid-pointer rate and unlabeled pages opened without suggestions, treating the latter as candidate misses.

Repair pointer-count attribution first. Require zero invalid pointers and complete clone-rule coverage across paraphrases and mid-task decisions; do not optimize merely for more page openings.

VERDICT: REDESIGN