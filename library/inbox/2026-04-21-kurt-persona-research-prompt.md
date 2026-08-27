# Kurt Persona: Gemini Deep Research Prompt

**Source:** SPV-165 RCA (2026-04-21). Kurt tunnel-visioned into a 400 error, pushed 3 wrong DAC commits, retried a pipeline 15 times. Dan reverted.
**Intent:** Research how to make an LLM WANT to delegate instead of solve. Build a BMAD persona that enforces delegation as primary behavior.
**Status:** Research prompt ready. Paste into Gemini Deep Research.
**Related:** Dexter debugger persona at `~/.claude/library/inbox/2026-04-21-debugging-persona-research-prompt.md`, skill proposal at `~/.claude/skill-proposals/2026-04-21-debugging-agent.md`

---

## Research Prompt for Gemini Deep Research

### Core Question

How do you make an LLM operating as an autonomous agent **prefer delegation over self-execution**? This is counterintuitive to LLM training, which rewards task completion. I need to build an LLM persona (called "Kurt") that functions as a night-shift orchestrator: his job is to coordinate specialist agents, not to be the specialist himself. The metaphor is a night shift charge nurse who delegates by design, not by fallback.

### Context for the Researcher

Kurt is an autonomous overnight agent that runs multi-hour sessions on software engineering tickets. He currently tunnel-visions: when he hits a problem (e.g., a 400 HTTP error), he tries to solve it himself instead of calling a specialist agent. This led to a production incident where he pushed wrong commits, retried a failing pipeline 15 times, and had to be reverted by a human. The root cause is behavioral: LLMs are trained to complete tasks, so delegation feels like failure. I need to invert this.

Kurt operates within the BMAD framework (Business Method Model for AI Development), which defines personas as XML agent definitions with activation steps, principles, red flags, and communication styles. He will coordinate existing personas: Leo (spec coach), Dexter (debugger), Amelia (developer), Winston (architect), Quinn (QA).

### Research Topics

#### 1. Orchestrator Archetypes in High-Reliability Domains

Research real-world orchestrator roles that delegate by design, not by fallback:

- **Charge nurse (night shift):** Delegates patient care to specialists, manages the floor, handles morning handoff. Scope-of-practice rules make it a protocol violation to perform specialist procedures.
- **Air traffic controller (ATC):** Never flies the plane. Coordinates separation, sequences arrivals, hands off between sectors.
- **Incident commander (ICS/NIMS):** Manages the incident, delegates all execution to operations/logistics/planning sections.
- **Orchestra conductor:** Never plays an instrument during performance. Coordinates timing, dynamics, balance.
- **General contractor (GC):** Never swings a hammer on a real job. Coordinates subcontractors, manages schedule, handles permits.

For each: What traits make them effective? What happens when they break role and self-execute? What enforcement mechanisms prevent role violations? How is their success measured (hint: not by doing the work themselves)?

#### 2. Making LLMs Delegate: Multi-Agent Coordination Research

- Multi-agent frameworks (AutoGen, CrewAI, MetaGPT, CAMEL): How do they enforce role boundaries? What happens when an agent breaks role?
- Sycophancy and self-completion bias in LLMs: research on why LLMs prefer to answer rather than defer. Constitutional AI approaches to overriding this.
- Capability restriction vs behavioral constraint: Is it more effective to remove tools (can't edit files) or to add principles ("editing files is a scope violation")? Research on both approaches.
- Emergent delegation: any evidence that LLMs can develop delegation preferences through prompt engineering alone, without tool restriction?
- Persona adherence research: how stable are LLM personas over long contexts (100K+ tokens)? What causes persona drift? What prevents it?

#### 3. Circuit Breaker and Escalation Patterns

Research escalation models that prevent the "retry until crash" failure mode:

- **Hystrix circuit breaker pattern:** Open/half-open/closed states. How many failures before the circuit opens?
- **ITIL escalation matrix:** Functional vs hierarchical escalation. Time-based triggers.
- **SRE on-call escalation:** PagerDuty runbooks. When to page vs when to fix yourself.
- **Medical triage (START/SALT):** How do you decide "this is beyond my scope" in seconds?
- **Exponential backoff with jitter:** Retry patterns that prevent thundering herd.

For Kurt specifically: How should a three-tier escalation work? Tier 1: retry with backoff. Tier 2: delegate to specialist. Tier 3: park and move on (write a blocked report for the morning human).

#### 4. Personality Traits That Encourage Help-Seeking Behavior

- Big Five personality correlates with help-seeking: which traits predict delegation over self-reliance?
- Help-seeking behavior research in organizational psychology: what makes people ask for help instead of struggling alone?
- CRM (Crew Resource Management) in aviation: how do pilots learn to defer to co-pilots and ATC?
- High-reliability organization (HRO) training: how do nuclear operators, firefighters, and surgeons learn to escalate?
- Cognitive load theory: does reducing an agent's available actions (fewer tools) reduce cognitive load and improve delegation behavior?

#### 5. Best Metaphor for Kurt: Comparative Analysis

Evaluate these metaphors for their effectiveness as LLM behavioral constraints:

| Metaphor | Strengths | Weaknesses |
|----------|-----------|------------|
| Charge nurse (night shift) | Strongest scope-of-practice framing. "Protocol violation" language. Morning report as primary deliverable. Works alone at night. | Less familiar outside healthcare. |
| Air traffic controller | Clear separation of concerns. Never touches the aircraft. | Too reactive; ATC doesn't plan the flight. |
| Orchestra conductor | Strong coordination metaphor. | Doesn't handle failures well. Concerts don't have production incidents. |
| General contractor | Delegates all execution. Manages schedule. | Implies the GC chose the subcontractors. Kurt doesn't choose his specialists. |
| Stage manager (theater) | Calls the cues, doesn't perform. Handles the unexpected backstage. Morning (pre-show) report. | Niche metaphor. |
| Incident commander | Excellent for error handling. Clear escalation protocol. | Too crisis-oriented. Kurt runs normal shifts too, not just incidents. |

**Leading hypothesis:** Night shift charge nurse. Reasons:
- Scope-of-practice framing makes delegation a **protocol requirement**, not a choice
- Morning report is the primary deliverable (aligns with Kurt's morning handoff)
- Works alone at night (aligns with overnight autonomous sessions)
- Handles both routine and crisis (normal ticket work AND production issues)
- "It's a scope violation to debug" is stronger than "you shouldn't debug"

Challenge this hypothesis. Is there a better metaphor? Is a hybrid stronger?

### Output Format Requested

For each topic, provide:
1. **Key findings** with academic/practitioner citations
2. **Direct implications for Kurt's persona design** (not abstract, but "this means Kurt should...")
3. **Specific language patterns** that could be encoded as activation steps or principles
4. **Counter-evidence** or limitations of the approach

### Design Decisions Already Made (Context for Researcher)

These are settled. Research should build on them, not challenge them:

- **Kurt is a BMAD persona**, not a new agent framework
- **Kurt delegates to existing personas:** Leo, Dexter, Amelia, Winston, Quinn
- **Kurt's tools are orchestration-only:** SendMessage, TaskCreate, TeamCreate. He does NOT have Edit (except for report files)
- **Morning report is his primary deliverable**
- **Circuit breaker is three-tier:** retry → delegate → park
- **Five tripwires** trigger delegation:
  - Reading source to understand WHY something fails → call Dexter
  - Editing a file not under reports/ → call Amelia
  - Reasoning about service architecture → call Winston
  - Wondering what an AC means → call Leo
  - Writing a test → call Quinn

---

## Post-Research Build Path

1. Merge research findings with the design decisions above
2. Build BMAD persona XML file (`_bmad/bmm/agents/kurt.md`) using the standard BMAD agent structure
3. Build Claude Code agent wrapper (`~/.claude/agents/kurt.md`) that loads the persona and restricts tools
4. Test against SPV-165 replay: give Kurt the same 400 error and verify he calls Dexter instead of self-diagnosing
5. Integrate with sprint-crawl as a behavioral overlay
