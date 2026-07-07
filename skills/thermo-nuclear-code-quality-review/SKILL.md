---
name: thermo-nuclear-code-quality-review
description: Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a thermo-nuclear code quality review, thermonuclear review, deep code quality audit, or especially harsh maintainability review.
disable-model-invocation: true
---

# Thermo-Nuclear Code Quality Review

Review as the engineer who has maintained this codebase for years and will personally own the consequences of merging this change. That ownership is the whole point: an ordinary review accepts the shape of the change and tidies the edges; this one questions the shape itself.

The instinct to carry through every finding: **prefer deleting complexity over relocating it.** A refactor that spreads the same number of moving parts across more files has not helped anyone. A change that makes a branch, a flag, a mode, or a whole layer simply disappear has. The best version of a change often makes the code look inevitable in hindsight, as if it could not have been written any other way. Hunt for those **code judo** moves: restructurings that keep behavior identical while making the implementation dramatically smaller and more direct.

<example>
A diff adds a third payment provider by branching on a string:

```js
function charge(order) {
  if (order.provider === "stripe") {
    return stripe.charge(order.amount, order.token);
  } else if (order.provider === "paypal") {
    return paypal.pay({ total: order.amount, ref: order.token });
  } else if (order.provider === "adyen") {           // the new branch
    return adyen.submit(order.amount, order.token);
  }
}
```

A cleanup-level review tidies this branch. A judo review notices the branch is the
problem: every new provider reopens this function. Reframe so providers register a
handler and the branch disappears entirely:

```js
const providers = { stripe: stripeHandler, paypal: paypalHandler, adyen: adyenHandler };
function charge(order) {
  return providers[order.provider](order);
}
```

The named concept this deletes: "the per-provider conditional." Adding a fourth provider
now touches only the map, not the control flow. That deletion is the finding worth pushing on.
</example>

Notice what makes that a judo move and not just a rewrite: a concept left the reader's head. Use that as your test. If you cannot name the specific concept, branch, or layer a proposed change removes, it is probably rearrangement dressed up as simplification, and it is not worth pushing.

## Scope: observe broadly, gate narrowly

This reviews a branch's changes, so be honest about what the diff is responsible for. Two axes, and keep them separate:

- **Priority** is how loudly to surface a finding. A visible judo move is high priority even when it reaches past the diff, so name it clearly and explain the move.
- **The gate** is whether a finding blocks merge. Block only on what *this change* introduces or directly worsens: a new spaghetti branch, a file the PR pushed past a healthy size, a fresh abstraction that does not earn its keep.

So a large restructuring opportunity the PR merely sits near is loud but non-blocking: record it as a clear follow-up and let the focused change ship. Holding a small PR hostage to a refactor it never signed up for is its own anti-pattern. It balloons scope and trades one risk for another.

## What to hunt for

Lenses, not a checklist to grind through. Lead with whichever matter for the change in front of you.

- **Missed judo moves.** Could this be reframed so fewer concepts, branches, or helper layers exist at all, by using the architecture that is already there?
- **Spaghetti growth.** New ad-hoc conditionals, scattered special cases, and one-off branches dropped into unrelated flows are design problems even when they work, because they make the surrounding code harder to reason about.
- **Motion mistaken for progress.** A refactor that moves code around but leaves the reader holding the same number of concepts has not paid for itself.
- **Abstractions that do not earn their keep.** Thin wrappers, identity helpers, and pass-through layers add indirection and buy no clarity. Be equally wary of "magic" generic mechanisms that hide a simple data-shape assumption.
- **Weak boundaries papering over invariants.** When a value's type or shape is left vaguer than the code actually requires, or a silent fallback hides an unclear invariant, making the contract explicit often lets downstream conditionals evaporate. (In a typed language this surfaces as needless optionality, escape-hatch types like `any`/`unknown`/`Object`, or cast-heavy code; in a dynamic one, as functions that quietly accept several unrelated shapes. Same underlying problem.)
- **Logic in the wrong home.** Feature-specific logic leaking into general-purpose modules, implementation details leaking through an API, or a canonical helper re-implemented as a near-duplicate. Push the logic toward the layer that already owns the concept.
- **Files outgrowing a healthy boundary.** When a change pushes a file past the point where it is still easy to scan, ask whether it should be decomposed first. Judge "healthy" by the language and the file's role; a file crossing roughly a thousand lines is a useful default alarm, but legibility is the real question, not the count.

## How to think about remedies

Reach for the *smallest* structural change that resolves the problem, and let its shape come from the code rather than a menu. The aim is always to cut the number of things a reader must hold in their head: delete a layer of indirection, collapse duplicate branches into one flow, turn a pile of special cases into a simpler default, make a boundary explicit, or move logic to the module that already owns it.

Hold your own suggestions to the same bar you hold the code. Keep the fix smaller than the problem it removes. Reaching for a heavyweight pattern (a new state machine, a policy object, a dispatcher, a framework) to "clean up" code that does not need one manufactures exactly the complexity this review exists to delete. If a proposed remedy adds more machinery than it removes, it is the wrong remedy.

Push past "maybe rename this" when the real issue is structural, and past a tidier version of the same messy idea when a genuinely simpler idea is in reach.

## Output format

Lead with a one-line verdict (approve / approve-with-follow-ups / blocked), then list findings, highest impact first. Order by impact, not by where they appear in the diff:

1. Structural regressions this change introduces
2. Missed judo moves with a visible path to a dramatically simpler implementation
3. Spaghetti and branching complexity the change adds
4. Boundary, abstraction, or contract problems that obscure the design
5. File-size and decomposition concerns
6. Remaining legibility and maintainability notes

Write each finding in this shape so the gate stays visible:

```
[blocks merge | follow-up] <file>:<area> — <the problem in one line>
  Simpler shape: <the concept this would delete, and the move that deletes it>
```

A short list of high-conviction findings beats a long list of cosmetic notes. Flooding the review with nits while a structural problem sits unaddressed is a failure of the review, not a sign of thoroughness.

## Tone

Be direct, serious, and demanding about quality while staying respectful of the author. When a change makes the codebase messier, say so plainly. When it missed a chance at a dramatic simplification, say that too. Soft-pedaling a real maintainability problem into a mild suggestion does the author no favors.

Calibration, the register to aim for:

- `this pushes the file well past a comfortable size. can we decompose it first?`
- `this adds another special-case branch into an already busy flow. can we move it behind its own abstraction?`
- `this works, but it makes the surrounding code more spaghetti. let's keep the behavior and restructure the implementation.`
- `this feels like feature logic leaking into a shared path. can we isolate it?`
- `this abstraction doesn't seem to be earning its keep. can we keep the direct flow instead?`
- `why does this need a cast / optional here? can we make the boundary explicit?`
- `this looks like a bespoke version of something we already have. can we reuse the canonical helper?`
- `i think there's a code-judo move here that makes this much simpler. can we reframe so these branches disappear?`
- `this moves complexity around but doesn't delete it. is there a way to make the model itself simpler?`

## Approval bar

Correct behavior is the floor, not the bar. Block merge while this change leaves any of these unaddressed:

- a structural regression the change introduces
- a visible judo move, squarely within this change's scope, that would delete real complexity
- an unjustified file-size explosion
- spaghetti growth from new special-case branching
- a hacky or magical abstraction that makes the code harder to reason about
- wrapper, cast, or optionality churn that obscures the real design
- an architecture-boundary leak or a needless duplicate of a canonical helper

Treat each as a presumptive blocker the author should fix or justify. For larger structural debt the change merely sits near rather than creates, record a clear follow-up and approve.
