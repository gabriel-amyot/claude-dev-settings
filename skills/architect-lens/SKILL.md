---
name: architect-lens
description: Apply the architect's method from Fundamentals of Software Architecture (Richards and Ford, Part 1) to a real problem. Identify and rank architecture characteristics from business drivers, run least worst trade-off analysis, count architecture quanta, define measures and fitness functions, choose partitioning and components, shortlist styles. Coach mode makes the user decide first and critiques with book citations. Do mode drafts the analysis. Triggers on "architect lens", "think like an architect", "architecture characteristics for", "which -ilities", "least worst", "trade-off analysis", "how many quanta", "fitness function for", "monolith or distributed", "which architecture style".
nav:
  bay: plan
  when: "Analyze a problem from the architect's point of view: characteristics, trade-offs, quanta, governance, components, style shortlist. Also for practicing the FoSA method."
  when_not: "Module or interface design inside code (codebase-design). Refactoring an existing codebase (improve-codebase-architecture). Writing the final ADR into a repo (push-adr). A full BMAD architecture document (Winston create-architecture)."
  personas: [winston]
---

# architect-lens

Apply Part 1 of *Fundamentals of Software Architecture* (FoSA) to a problem, as an architect. The user is learning to be a better architect. The goal is a better decision **and** a better architect.

## Host compatibility

Read [the shared host mapping](../../docs/skill-host-compatibility.md) before execution. This skill uses only file reads, `grep` and file writes. It works the same in Claude Code and Codex.

## The knowledge base

The book lives in a local knowledge base, outside this repo:

```
FOSA_KB="${FOSA_KB:-$HOME/Developer/gabriel-amyot/resources/Fundamentals of Software Architecture/kb}"
```

- **Progressive disclosure.** Read `$FOSA_KB/INDEX.md` once (task router). Then read the chapter `study.md` or `INDEX.md` for summaries. Open a section file only when you need the detail or a citation. Use the section frontmatter (`head -20`) to decide before you load a section. Never read `source/book.md`.
- **Routing per step:** [references/kb-routing.md](references/kb-routing.md).
- **Read budget.** The KB's "router plus one file" rule is for a single question. A mode runs several steps: read at most the router once, then one or two files per step. Read frontmatter before any full section.
- **If `$FOSA_KB` does not exist:** say so in one line, once. Run the method from [references/method.md](references/method.md) only. Put one "Uncited: the knowledge base is not available" line at the top of the output instead of a marker on every line, and never write a `Ch N §Section` citation you did not read.
- **Copyright.** Quote at most one short phrase. Paraphrase and cite. Never copy book text into a repo, a PR, a ticket or any external post.

## Start: three questions

Ask these together, in one message, unless the request already answers them:

1. **Problem.** What system or decision? Who are the users? What does the business need to succeed?
2. **Mode.** Which step? `characteristics` · `tradeoffs` · `quanta` · `governance` · `components` · `styles` · `worksheet` (all steps in order) · `review` (critique an existing design or document).
3. **Stance.** `coach` (you answer first, I critique with citations) or `do` (I draft, you review). Default: `coach` when the user says learn, practice or study. Otherwise `do`.

If the business drivers are vague, offer the `grilling` skill to interview the user before the analysis.

## Coach stance (the learning loop)

For each step:

1. **Ask** the step's question (from [references/method.md](references/method.md)). Give the user the minimum context. Do not show your answer yet.
2. **Wait** for the user's answer.
3. **Critique.** Compare the answer to the method. Name what is strong, what is missing and what is wrong. Each point cites `Ch N §Section` with the KB path.
4. **Reveal** your own version of the step, marked as yours.
5. **One recall question** from the chapter's `study.md` when the gap shows a missing concept. Point to the section to read. Do not lecture.

Keep each turn short. One step per turn. The user can say `skip`, `do it` (switch to do stance for this step) or `deeper` (open the section and explain).

## Do stance

Run the steps and draft each one. Mark every assumption as `ASSUMPTION:` and every inference not in the book as `MY INFERENCE:`. End with the open questions that would change the result.

## The steps

Full method, questions and checks: [references/method.md](references/method.md). Summary:

| Step | Question | Output |
|---|---|---|
| characteristics | Which architecture characteristics does this problem need, and which three matter most? | Candidates (explicit, implicit, from domain concerns), the justified list, the top 3 from it, the reason for each |
| governance | How will we know each top characteristic holds, now and later? | Objective definition per characteristic, measure type, fitness function idea |
| quanta | How many independently deployable units with different characteristic needs? | Quanta list, the characteristics per quantum, monolith or distributed |
| components | How do we partition, and what are the first components? | Technical or domain partitioning with the reason, initial components, entity trap check |
| styles | Which styles fit the top characteristics? | Shortlist of 2 or 3 styles with ratings from `reference/styles-ratings.json` and the decision criteria of Ch 18 |
| tradeoffs | What do we gain and lose with each option? Which is least worst? | Options table (gains, losses, mitigations), the choice, the reason, an ADR stub |

`worksheet` runs them in this order: characteristics, governance, quanta, components, styles, tradeoffs.

## Rules of the method (hold these in every mode)

- Everything is a trade-off. If the analysis shows an option with no downside, look again.
- The reason for a decision matters more than the mechanism. Every recommendation states its why.
- Aim for the least worst architecture, not the best. Keep the justified list short, and challenge any item that is not critical or important. Then pick the top three from that list to guide trade-offs. The top three do not delete the other justified characteristics.
- Characteristics are often implicit. Ask about the ones nobody stated (availability, security, reliability).
- Translate business words into characteristics. "Time to market" is not one characteristic. Break it down.
- Characteristics can differ per quantum. A single system-wide list hides this.
- A characteristic without an objective definition cannot be governed.
- Prefer an architecture that is easy to change, because the first answer is rarely complete.

## Output

Write the worksheet with [templates/worksheet.md](templates/worksheet.md).

- **Where.** In a ticket context, write to the ticket folder under `reports/architecture/` (never into a service repo). Otherwise ask. Default: `./architecture-lens/<slug>-worksheet.md`.
- **Casebook.** Also append one line to `$FOSA_KB/../journal/CASEBOOK.md`: date, problem, mode, top 3, decision, worksheet path. This builds the user's personal casebook of applied architecture.
- **Study site bridge.** On `worksheet` mode, also write `$FOSA_KB/../journal/<slug>.fosa.json` in the study site's import format (see the template file). The user imports it in `site/apply.html`.

## Handoffs

| When | Hand off to |
|---|---|
| Drivers are vague, the user cannot state the business goal | `grilling` |
| A recommendation is ready and needs a stress test | `challenge` |
| The decision is settled and needs an ADR in a repo | `push-adr` (or `domain-modeling` for its ADR format) |
| The question is about module interfaces inside the code | `codebase-design` |
| The user wants a full architecture document | BMAD Winston, `[CA] Create Architecture` |

## Close every session with

1. The decision or the next decision, in one sentence.
2. The one concept the user should reread, with its KB path.
3. The casebook line written.
