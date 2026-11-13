# The architect's method (FoSA Part 1), step by step

Original summary for the `architect-lens` skill. It paraphrases the method of *Fundamentals of Software Architecture* (Richards and Ford, 1st ed.). It contains no book text. For the source, follow the KB paths in [kb-routing.md](kb-routing.md).

Each step has: the **question** to ask (coach stance asks it first), the **moves** (how to answer), and the **checks** (what a critique looks for).

## Laws that frame every step (Ch 1, Ch 2)

- First law: everything in software architecture is a trade-off. "It depends" is a valid answer only when you name what it depends on.
- Second law: why is more important than how.
- Architecture is the structure, the characteristics, the decisions and the design principles. A step that ignores one of these is incomplete.
- Architectural thinking: collaborate with developers, keep technical breadth, analyze trade-offs, understand the business drivers.

## Step 1. characteristics

**Question.** Which architecture characteristics must this system support to succeed, and which three matter most?

**Moves.**
1. List the business drivers and domain concerns in the stakeholders' words.
2. Translate each concern into characteristics. One concern often maps to several. Example pattern: a concern about speed of change maps to agility, which itself breaks into testability, deployability and modularity.
3. Read the requirements for explicit characteristics. Look for hidden numbers: user counts, bursts, deadlines, geographic spread.
4. Add implicit characteristics that nobody states but everyone expects (availability, reliability, security). Ask which ones are architectural here and which are design concerns.
5. Test each candidate: is it a non-domain consideration, does it influence the structure, and is it critical or important to success? If not, it is a design concern or a nice-to-have.
6. Keep the full justified list: every characteristic that passes the test stays, with its reason. The list must stay short, because each supported characteristic adds design complexity.
7. From that final list, ask the stakeholders for the top three, in any order. Do not try to rank the whole list. The top three guide trade-offs. They do not delete the other justified characteristics.
8. Try to remove the least important characteristic from the full list and see if the design gets simpler.

**Checks.**
- A long list where several items fail the test above: challenge each one. Over-specifying hurts as much as under-specifying. (Coaching heuristic, not a book rule: a list much longer than about seven usually hides design concerns.)
- The top three confused with the whole list, so important characteristics get dropped.
- A business concern copied as is ("time to market") without translation.
- Implicit characteristics missing, especially availability and security.
- A characteristic named but not tied to a driver: ask why it is there.
- A domain requirement disguised as a characteristic. Test: does it need domain knowledge to implement? Then it is a requirement.

## Step 2. governance (measure and protect)

**Question.** How will we know that each top characteristic holds today, and how will we notice when it degrades?

**Moves.**
1. Write an objective definition for each top characteristic, agreed with the team. Break composite ones into measurable parts.
2. Pick the measure type: operational (latency, throughput, availability), structural (complexity, coupling, cycles), or process (deploy frequency, test coverage, lead time).
3. Use percentiles or maximums, not only averages.
4. Design a fitness function for each: any objective check (a test, a metric threshold, a monitor, a chaos experiment, an architecture rule test) that runs in the build or in production.
5. Explain each fitness function to the developers before you impose it.

**Checks.**
- A characteristic with no objective definition: it cannot be governed.
- Only averages: outliers hide.
- A fitness function that nobody runs (not in CI, not scheduled).
- Structural rules (layer boundaries, no cycles) left to code review alone.

## Step 3. quanta (scope of characteristics)

**Question.** How many architecture quanta does this system have, and does each one need the same characteristics?

**Moves.**
1. A quantum is an independently deployable unit with high functional cohesion and synchronous coupling inside it. Include its runtime dependencies, such as its database.
2. Draw each deployable unit with its data store. A shared database usually merges units into one quantum.
3. Mark synchronous calls between units. Synchronous calls share operational characteristics: a fast caller depends on a slow callee.
4. Assign characteristics per quantum. Look for parts with different needs (for example, a bursty part that needs elasticity next to a part that needs strict consistency).
5. Decide: one set of characteristics for the whole system favors a monolith. Several different sets push toward a distributed architecture.
6. Where different quanta must cooperate, consider asynchronous links to decouple their characteristics.

**Checks.**
- One system-wide list when parts clearly differ.
- "Microservices" claimed while every service shares one database or calls the others synchronously (one quantum in practice).
- A distributed choice with no part that needs different characteristics: the cost of distribution (the fallacies of distributed computing, Ch 9) buys nothing.

## Step 4. components (partitioning)

**Question.** How do we partition the system at the top level, and what are the first components?

**Moves.**
1. Choose top-level partitioning: technical (layers by capability) or domain (by business workflow). State why. Check the fit with team structure (Conway's law; the inverse Conway maneuver).
2. Identify initial components with a discovery technique that fits the context: actor/actions, event storming, or workflow.
3. Assign requirements to components. Check that each component has a clear role and responsibility.
4. Analyze the characteristics per component. Split a component when its parts need different characteristics.
5. Restructure. Expect several iterations. The first set is rarely right.

**Checks.**
- The entity trap: components that mirror database tables or entities (a "manager" per table) instead of workflows.
- Technical partitioning chosen by habit when changes arrive per domain.
- Component granularity too fine (chatty) or too coarse (no clear role).

## Step 5. styles (shortlist)

**Question.** Which two or three architecture styles fit the top characteristics and the context?

**Moves.**
1. Start from step 3: monolith or distributed.
2. Load `reference/styles-ratings.json`. Score each style on the top characteristics. Treat the stars as a starting point, not a verdict.
3. Walk the decision criteria of Ch 18: the domain, the structural characteristics, the data architecture, organizational factors, process and team maturity, domain to architecture fit, where data lives, synchronous or asynchronous communication.
4. Read the "when to use" and "avoid when" of each shortlisted style card.
5. A hybrid is normal when quanta differ.

**Checks.**
- A style chosen because it is fashionable.
- Ratings used for characteristics the book does not rate (say so, and reason from the style chapter).
- Data architecture and team maturity ignored.

## Step 6. tradeoffs (least worst decision)

**Question.** What do we gain and what do we lose with each option, and which option is the least worst?

**Moves.**
1. State the decision and its context: the forces that require it.
2. List at least two real options. Include the status quo when it exists.
3. For each option, list gains and losses against the top characteristics, plus cost, complexity, risk and team fit. Name the mitigation for each loss.
4. Trace consequences one level further: what does each option make harder later?
5. Choose the least worst option. State the why in one or two sentences.
6. Prefer the option that is easier to change if the evidence is weak.
7. Write an ADR stub: Title, Status, Context, Decision (affirmative voice, with the why), Consequences, Compliance (how it is governed), Notes.

**Checks.**
- An option with no downside listed.
- Only one option analyzed.
- The decision states how but not why.
- No compliance line: the decision cannot be verified.
- A decision that belongs to design or to a developer, dressed as architecture. Test: does it affect structure, dependencies, interfaces, construction techniques or a top characteristic?

## Review mode

Read the user's design or document. Run the checks of every step against it. Report per step: what holds, what is missing, what is wrong. **Every finding carries its own citation** in the form `Ch N §Section (path)`, including findings that restate a law or a rule from this file. A reference file is a valid source when you name the chapter behind it, for example `reference/styles-ratings.md (Ch 17 ratings)`. A finding you cannot tie to a section is marked `MY INFERENCE`. Then name the single highest-risk gap.
