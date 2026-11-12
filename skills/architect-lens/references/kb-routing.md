# KB routing for architect-lens

Every path below is relative to `$FOSA_KB` (default `~/Developer/gabriel-amyot/resources/Fundamentals of Software Architecture/kb`) and resolves as written. Read in the order given. Stop as soon as you have enough.

Cheap first: `study.md` (takeaways, recall) and `INDEX.md` (section summaries). Section files only for detail or a citation. To check a section before loading it, read its frontmatter: `head -20 <file>`.

Shorthand used below:

- `P0` = `part-0-introduction/ch01-introduction`
- `C2` = `part-1-foundations/ch02-architectural-thinking`
- `C3` = `part-1-foundations/ch03-modularity`
- `C4` = `part-1-foundations/ch04-architecture-characteristics-defined`
- `C5` = `part-1-foundations/ch05-identifying-architectural-characteristics`
- `C6` = `part-1-foundations/ch06-measuring-and-governing-architecture-characteristics`
- `C7` = `part-1-foundations/ch07-scope-of-architecture-characteristics`
- `C8` = `part-1-foundations/ch08-component-based-thinking`
- `C9` = `part-2-styles/ch09-foundations`
- `C18` = `part-2-styles/ch18-choosing-the-appropriate-architecture-style`
- `C19` = `part-3-techniques/ch19-architecture-decisions`
- `C20` = `part-3-techniques/ch20-analyzing-architecture-risk`

| Step | First read | Then, only if needed |
|---|---|---|
| Laws, definitions | `P0/04-laws-of-software-architecture.md` | `P0/INDEX.md` |
| Architectural thinking, trade-offs | `C2/study.md` | `C2/03-analyzing-trade-offs.md`, `C2/04-understanding-business-drivers.md` |
| characteristics | `C5/study.md`, `reference/characteristics.md` | `C5/01-extracting-architecture-characteristics-from-domain-concerns.md` (domain concern translation table), `C5/02-extracting-architecture-characteristics-from-requirements.md` (katas), `C5/03-case-study-silicon-sandwiches.md`, `C4/00-overview.md` (what makes a characteristic), `C4/01-architectural-characteristics-partially-listed.md` |
| least worst | `C4/02-trade-offs-and-least-worst-architecture.md` (short) | |
| governance | `C6/study.md` | `C6/01-measuring-architecture-characteristics.md`, `C6/02-governance-and-fitness-functions.md` (note: four code examples are source gaps, see the warning in the file) |
| quanta | `C7/study.md` | `C7/02-architectural-quanta-and-granularity.md`, `C8/08-architecture-quantum-redux-choosing-between-monolithic-versu.md` |
| components | `C8/study.md` | `C8/02-architect-role.md` (partitioning), `C8/04-component-identification-flow.md`, `C8/06-component-design.md` (discovery techniques, entity trap), `C8/07-case-study-going-going-gone-discovering-components.md` |
| modularity metrics (for governance) | `C3/study.md` | `C3/04-measuring-modularity-distance-from-the-main-sequence.md`, `C3/05-measuring-modularity-connascence.md` |
| styles | `python3 ../tools/rank_styles.py <char> <char> <char>` (ranks with ties), `reference/styles-ratings.md` (style cards), `reference/techniques.md` (Ch 18 criteria) | the style chapter `INDEX.md` in `part-2-styles/`, `C18/02-decision-criteria.md` |
| distributed costs | `C9/study.md` | `C9/02-monolithic-versus-distributed-architectures.md` (the fallacies) |
| tradeoffs, ADR | `reference/techniques.md` (ADR template) | `C19/03-architecture-decision-records.md`, `C19/02-architecturally-significant.md`, `C19/01-architecture-decision-anti-patterns.md` |
| risk | `C20/study.md` | `C20/01-risk-matrix.md`, `C20/03-risk-storming.md` |
| a term you do not know | `grep -i -m3 "<term>" reference/glossary.md` | `grep -i -A2 "<term>" reference/concept-index.md`, then the linked section file |

## Citation format

`Ch 7 §Architectural Quanta and Granularity` followed by the path, for example `(kb/part-1-foundations/ch07-scope-of-architecture-characteristics/02-architectural-quanta-and-granularity.md)`.
