# Style Charter — Powers MCP `agent-os/` Documentation

Binding rules for every document and code comment in `app-ttd-trading-mcp`. Distilled from Gabriel's 2026-09-11 review of the agent-os tree. Every editor pass and every verifier pass judges against this charter. A charter violation in a shipped document is a Major finding.

## 1. Indexes are indexes

- An INDEX.md contains pointers and a one-line role per document. Nothing else.
- No corrections, no convention history, no related-ticket lists, no cross-repo narratives.
- A standing directive (a rule the reader must obey when using the tree) may stay in the INDEX. Everything that is not a pointer, a role line, or a standing directive moves out or dies.
- A read order is welcome: list the documents in the order a fresh reader should consume them, one defining line each.

## 2. Contracts state the current truth only

- No strike-throughs. No dates. No "today", "currently", "as of", "recently", "was", "used to".
- Strike-and-annotate is legal ONLY in ADRs and CHANGELOG.
- A contract defines inputs, outputs, behavior, and error modes. If a section does not define one of those, it does not belong in a contract.
- Corrections are invisible: the contract reads as if it had always been right.

## 3. Tickets and dates live in decision records only

- Ticket keys (KTP-XXXX) and dates are allowed only in ADRs and CHANGELOG.
- Everywhere else, state the fact. The git history carries the provenance.

## 4. No project-management paths in the repo

- No path under `project-management/`, no `tickets/...`, no local absolute paths, anywhere in the MCP repo (docs or comments).
- External references are repo-relative links or GitLab URLs.

## 5. Cite by symbol, never by line number

- Wrong: `server.py:412`. Right: `server.py::propose_bid_change` or "`BidSafety.check` in `bid_safety.py`".
- Line numbers rot on the next commit. Symbols survive refactors and are searchable.

## 6. Positive phrasing first

- Lead with what the system does: "X does Y." A negative guarantee ("X never does Z") may follow as a second sentence, never lead a section.
- Exception: a safety invariant whose whole content is a prohibition may state the prohibition directly.

## 7. Define every term

- Jargon gets a definition at first use or a GLOSSARY.md entry. No unexplained terms ("loopback rehearsal", "walk", "seat").
- One name for one thing across the whole tree. No synonym rotation.

## 8. Table-first

- If a fact fits a column, it is a column. Cells hold one or two words.
- Details and edge cases demote to an Examples section below the table, not into the cells.

## 9. Register: STE / short declaratives

- One idea per sentence. Active voice. Minimum words.
- No meta-commentary (no "this document describes", no "note that", no narration of how the doc was produced).
- No "trust me" claims (no "robust", "comprehensive", "battle-tested"). State the guarantee or omit the sentence.
- No em-dash as a sentence separator. Em-dash is legal only as a heading label.
- No semicolons. Write two sentences.

## 10. ADR supersession: banner + fold

- The ADR INDEX carries a single status word per ADR: Accepted, Amended, Abandoned, or Superseded. No prose glosses.
- Inside a superseded or amended ADR: a dated banner at the top names what replaced which clause. Dead detail folds into a `<details>` block. History stays intact below the fold.

## 11. Code comments carry only the why

- A comment states the constraint the line cannot show. Nothing else.
- Specification prose belongs in `agent-os/`. The code keeps a one-line pointer to the doc (repo-relative path).
- No meta-commentary, no ticket keys, no dates, no model rationale, no "changed because review said so" in comments or docstrings.
- Type hints replace type-prose. A docstring never restates the signature.
- MCP tool descriptions are prompts. Review them as prompts: what does the model need to pick this tool and call it right, in the fewest words.
- GraphQL documents get inline `#` field comments only where a field-specific fact exists (a unit, a trap, a server-side default).

## 12. No absolute claim without a mechanism (the anti-bullshit rule)

- Every absolute claim about runtime behavior ("always", "every", "never", "only", "exactly one", "guaranteed") names the enforcing mechanism by symbol.
- No single mechanism enforces it = the absolute claim is forbidden. State the honest weaker claim (best-effort, the normal path) and enumerate the exceptions by symbol.
- When a reviewer refutes a claim that already survived one reformulation, the claim itself is the defect. Remove it or demote it. Rewording it again is forbidden.
- Litmus: for each absolute sentence ask "what one code path would falsify this?" If you can name one, the sentence is wrong before any reviewer reads it.

## 13. Hard boundary for this flow

- Zero executable-code changes in `.py` files. Comments and docstrings only. `ast-guard.py` enforces this mechanically every round.
- `.md` files may be rewritten freely within the scope manifest.
