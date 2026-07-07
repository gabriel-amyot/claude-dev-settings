#!/usr/bin/env python3
"""
verify-causal-claims.py — KTP-907 gate for the /post-comment pipeline.

Scans a drafted external post for CAUSAL claims (root-cause assertions, defect attribution)
and for BLAME language (attributing a defect to a named person's code). Complements
verify-code-claims.py, which checks WHERE a cited line lives (branch provenance); this gate
checks whether a stated WHY is backed by evidence against the actual failing input.

The catastrophe this prevents: asserting a mechanism reproduced in isolation as the confirmed
root cause and posting it publicly against a colleague's code (KTP-907: Decimal blamed, real
cause was Altair's 5,000-row cap; retracted after the colleague pushed back).

A causal claim is publishable only when one of these travels WITH it in the draft:

  Confirmed-in-context: <path-to-validation-artifact>
      The mechanism was demonstrated against the ACTUAL failing input/path. The artifact must
      (a) exist, (b) not be the draft itself, and (c) be a falsification PRODUCT — it must
      contain structured evidence markers (`Repro-command:` and `Observed:`, or
      `Falsified-against-input:`). A prose file asserting "I ran it locally" is not evidence.

  Per the published RCA <link/key> / As documented in <link>
      Quoting a cause that is ALREADY published and settled is allowed — the approver should
      verify the reference is real.

  [HYPOTHESIS — reproduced in isolation]   (or a line `Epistemic-status: hypothesis`)
      Honest, explicit uncertainty. Allowed (like UNVERIFIED in the code-claims gate) but
      surfaced loudly; if the hypothesis also names specific code (file:line), it is
      blame-adjacent and gets an escalated warning.

BLAME language (naming a person as the source of a defect) has NO override: confirmed or not,
external artifacts describe code and behavior, never authors. Reframe, then re-run.

NOTE: this regex layer is a BACKSTOP. The post-comment agent instructions are the first line
of defense and own what regex cannot see: correlational causation ("stopped working when we
switched to X") and subtle blame-by-name ("Sisi introduced the cast that ...").

On success this gate emits a marker file (/tmp/.pce-gate-pass) recording the draft path, hash
and timestamp, for the external-post choke-point hook to check.

Exit codes:
  0 — OK to proceed (no causal claims; confirmed with a substantive artifact; published-RCA
       quote; or explicitly labeled HYPOTHESIS — printed as a loud warning).
  2 — BLOCK: unlabeled causal claim, dangling/hollow/self-referential artifact, or blame.

Usage: verify-causal-claims.py <draft-file>
"""
import hashlib
import os
import re
import sys
import time

CAUSAL = re.compile(
    r'root[- ]cause'
    r'|root\s+of\s+the\s+(?:problem|issue|bug|failure)'
    r'|caus(?:ed|es|ing)\s+(?:by|the|this|it)'
    r'|the\s+(?:bug|problem|issue|defect|failure)\s+(?:is|was|lies|lives)\s+in'
    r'|bug\s+in\s+[\w`./]'
    r'|introduced\s+(?:by|in|with)\s'
    r'|culprit'
    r'|responsible\s+for\s+the'
    r'|boils?\s+down\s+to'
    r'|direct\s+(?:result|consequence)\s+of'
    r'|(?:broke|broken|breaks|fails?|failing|crashed?|regressed)\s+because'
    r'|because\s+of\s+(?:a|the|this)\s+(?:bug|change|commit|line|regression)'
    r'|due\s+to\s+(?:a|the|this)\s+(?:bug|change|commit|line|regression)'
    r'|regression\s+(?:from|introduced)'
    r'|(?:this|that|the)\s+(?:line|change|commit|code)\s+(?:causes|caused|breaks|broke)'
    r'|traced\s+(?:this|it|the\s+\w+)\s+(?:back\s+)?to'
    r'|stems?\s+from'
    r'|came\s+from\s+(?:the|a|that)\s+(?:refactor|change|commit|migration)'
    r'|turn(?:s|ed)\s+out\s+.{0,60}\b(?:was|is)\s+(?:the\s+)?(?:reason|cause|why|problem)'
    r'|(?:the\s+)?reason\s+(?:charts?|it|this|the\s+\w+)\s+'
    r'(?:fail|stopped|broke|went|are|is|didn.t)'
    r'|(?:is|was|be|[\'’]s)\s+(?:what|why)\s+(?:broke|breaks|caused|causes|fails|hid|hides)'
    r'|silently\s+(?:swallow|drops?|discard)'
    r'|quietly\s+(?:swallow|drops?|discards?|returns)'
    r'|anti[- ]pattern',
    re.IGNORECASE,
)

# --- blame detection: person as the source of a defect. No override. ---
# Innocent-token lessons (red-team 2026-07-07): no bare `blame`, no `git blame`, and a
# possessive alone ("Marc's change") is NOT blame — it needs causal force on the same line.
BLAME_NOUN = (r'(?:code|change|changes|commit|line|refactor|mr|pr|function|method|module|'
              r'query|regex|serializer|template|except|handler)')
TEMPORAL = r'(?:today|yesterday|tomorrow|week|month|year|sprint|monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
SUBJECT_STOPWORDS = {'this', 'the', 'it', 'that', 'we', 'they', 'someone', 'somebody',
                     'nobody', 'which', 'what', 'who', 'i', 'you'}
BLAME_VERB = r'(?:introduced|broke|breaks|caused|causes|hid|hides|swallowed|swallows|dropped)'

POSSESSIVE = re.compile(r"\b(\w+)['’]s\s+" + BLAME_NOUN + r'\b', re.IGNORECASE)
POSSESSIVE_VERB = re.compile(
    r"\b(\w+)['’]s\s+" + BLAME_NOUN + r'\s+' + BLAME_VERB, re.IGNORECASE)
YOUR_BLAME = re.compile(
    r'\byou(?:r)?\s+' + BLAME_NOUN + r'\s+(?:\w+\s+){0,3}?' + BLAME_VERB
    + r'|\byou\s+(?:introduced|broke|caused|wrote|added|committed)\b',
    re.IGNORECASE)
NAMED_SUBJECT = re.compile(
    r'\b([A-Z][a-z]+)\s+(?:introduced|broke|caused|added|wrote|committed|pushed)\b')
WROTE_THE_BUG = re.compile(
    r'\b(?:wrote|added|committed)\s+(?:this|that|the)\s+(?:bug|defect|broken)', re.IGNORECASE)
BLAME_NEGATION = re.compile(
    r"blameless|no\s+blame|not\s+blaming|don['’]t\s+blame|no\s+one\s+to\s+blame"
    r"|nobody['’]s\s+fault|not\s+\w+['’]s\s+fault", re.IGNORECASE)

CONFIRMED = re.compile(r'^\s*(?:>?\s*)?Confirmed-in-context:\s*(?P<ref>.+?)\s*$',
                       re.IGNORECASE | re.MULTILINE)
CONFIRMED_INLINE = re.compile(r'\[CONFIRMED-IN-CONTEXT:\s*(?P<ref>[^\]]+)\]', re.IGNORECASE)
PUBLISHED = re.compile(
    r'per\s+the\s+(?:published\s+)?RCA|as\s+documented\s+in\s|as\s+established\s+in\s'
    r'|per\s+the\s+post[- ]?mortem', re.IGNORECASE)
HYPOTHESIS = re.compile(r'\[HYPOTHESIS\b|^\s*Epistemic-status:\s*hypothesis\b',
                        re.IGNORECASE | re.MULTILINE)
ARTIFACT_MARKERS = re.compile(
    r'Repro-command:|Falsified-against-input:|Observed:', re.IGNORECASE)
CODE_CITATION = re.compile(
    r'\b[\w./\-]+\.(?:py|ts|tsx|js|jsx|java|go|rb|sql|kt|kts|rs|c|cc|cpp|h|hpp|scala|php'
    r'|swift|m|mm):\d+(?:-\d+)?\b')
PATHLIKE = re.compile(r'^[\w~./\-]+(?:\.\w+)?(?:#.*)?$')

MARKER_PATH = "/tmp/.pce-gate-pass"


def causal_hits_in(lines):
    return [(i, m.group(0), l.strip()) for i, l in enumerate(lines, 1)
            for m in CAUSAL.finditer(l)]


def blame_hits_in(lines):
    """Blame = person tied to a defect. Possessives/names need causal force on the line."""
    hits = []
    for i, line in enumerate(lines, 1):
        if BLAME_NEGATION.search(line):
            continue
        line_causal = bool(CAUSAL.search(line))
        for m in POSSESSIVE.finditer(line):
            owner = m.group(1).lower()
            if owner in SUBJECT_STOPWORDS or re.fullmatch(TEMPORAL, owner, re.IGNORECASE):
                continue
            if line_causal or POSSESSIVE_VERB.search(line):
                hits.append((i, m.group(0), line.strip()))
        m = YOUR_BLAME.search(line)
        if m and line_causal:
            hits.append((i, m.group(0), line.strip()))
        for m in NAMED_SUBJECT.finditer(line):
            if m.group(1).lower() in SUBJECT_STOPWORDS:
                continue
            if line_causal:
                hits.append((i, m.group(0), line.strip()))
        m = WROTE_THE_BUG.search(line)
        if m:
            hits.append((i, m.group(0), line.strip()))
    return hits


def resolve_refs(text, draft_path):
    """Collect Confirmed-in-context refs; return (refs, problems).
    A ref is only valid if it exists, is not the draft itself, and contains
    structured falsification markers (Repro-command:/Observed:/Falsified-against-input:)."""
    refs, problems = [], []
    for m in list(CONFIRMED.finditer(text)) + list(CONFIRMED_INLINE.finditer(text)):
        ref = m.group('ref').strip()
        refs.append(ref)
        candidate = ref.split('#')[0].strip().strip('`')
        if not (PATHLIKE.match(candidate) and '/' in candidate):
            problems.append((ref, "not a file path — point it at the falsifier's artifact file"))
            continue
        path = os.path.expanduser(candidate)
        if not os.path.exists(path):
            problems.append((ref, "does not exist on disk"))
            continue
        if os.path.realpath(path) == os.path.realpath(draft_path):
            problems.append((ref, "points at the draft itself — self-certification"))
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                artifact = fh.read()
        except OSError as e:
            problems.append((ref, f"unreadable: {e}"))
            continue
        if not ARTIFACT_MARKERS.search(artifact):
            problems.append((ref, "exists but contains no falsification evidence markers "
                                  "(needs `Repro-command:` + `Observed:` or "
                                  "`Falsified-against-input:`) — prose asserting a conclusion "
                                  "is not a validation artifact"))
    return refs, problems


def emit_marker(draft_path):
    try:
        with open(draft_path, 'rb') as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:16]
        with open(MARKER_PATH, 'w', encoding='utf-8') as fh:
            fh.write(f"{int(time.time())} {digest} {os.path.realpath(draft_path)}\n")
    except OSError:
        pass  # marker is best-effort; the hook treats absence as block


def main():
    if len(sys.argv) < 2:
        print("usage: verify-causal-claims.py <draft-file>", file=sys.stderr)
        return 2
    draft_path = sys.argv[1]
    try:
        with open(draft_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print(f"verify-causal-claims: cannot read draft: {e}", file=sys.stderr)
        return 2

    lines = text.splitlines()
    causal_hits = causal_hits_in(lines)
    blame_hits = blame_hits_in(lines)

    if blame_hits:
        print("BLOCKED by verify-causal-claims: BLAME language — a defect attributed to a named"
              " person or their code.\n", file=sys.stderr)
        for lineno, term, line in blame_hits:
            print(f"  line {lineno}: matched '{term}'", file=sys.stderr)
            print(f"            in: {line}", file=sys.stderr)
        print("\nExternal artifacts describe code and behavior, never authors (KTP-907 rule).\n"
              "There is no override for this — a CONFIRMED cause still doesn't need an author in\n"
              "the narrative. FIX: describe what the code does; if ownership matters, tag the\n"
              "person as reviewer/decision-maker ('fix options below — {name}'s call'), with no\n"
              "causal claim about their code. Then re-run the gate.", file=sys.stderr)
        return 2

    if not causal_hits:
        print("verify-causal-claims: OK — no causal/blame claims detected.")
        emit_marker(draft_path)
        return 0

    refs, problems = resolve_refs(text, draft_path)
    hypothesis = bool(HYPOTHESIS.search(text))
    published = bool(PUBLISHED.search(text))

    if problems:
        print("BLOCKED by verify-causal-claims: Confirmed-in-context reference(s) that do not"
              " hold up:\n", file=sys.stderr)
        for ref, why in problems:
            print(f"  {ref}\n      -> {why}", file=sys.stderr)
        print("\nA validation artifact must be a falsification PRODUCT: written by a"
              " fresh-context falsifier\nrun against the ACTUAL failing input, containing"
              " `Repro-command:` and `Observed:` lines\n(or `Falsified-against-input:`)."
              " Produce it, then re-run.", file=sys.stderr)
        return 2

    if refs:
        print("verify-causal-claims: proceeding — causal claim(s) reference a validation"
              " artifact:")
        for ref in refs:
            print(f"    {ref}")
        print("  PREVIEW BANNER (verbatim, for the approver):")
        print("    Author claims confirmation against the actual failing input."
              " Artifact: " + "; ".join(refs))
        print("    APPROVER: open the artifact and check it names the ACTUAL failing input"
              " and a repro command before approving.")
        emit_marker(draft_path)
        return 0

    if published:
        print("verify-causal-claims: proceeding — causal statement quotes an already-published"
              " RCA/postmortem.")
        print("  APPROVER: verify the referenced RCA is real and actually settled"
              " (link or ticket key present).")
        emit_marker(draft_path)
        return 0

    if hypothesis:
        cited = [c for l in lines for c in CODE_CITATION.findall(l)]
        print("⚠ verify-causal-claims: proceeding, but this draft states a CAUSE labeled as"
              " HYPOTHESIS —")
        print("  make sure the human approver sees that banner before this goes out:")
        for lineno, term, line in causal_hits[:5]:
            print(f"    line {lineno}: '{term}' in: {line}")
        if cited:
            print("  ⚠⚠ ESCALATED: this hypothesis names specific code (" + ", ".join(cited[:5])
                  + ").")
            print("     A public hypothesis pointing at someone's specific code is"
                  " blame-adjacent: the")
            print("     cheap label is NOT enough here — run the fresh-context falsifier and"
                  " upgrade to")
            print("     Confirmed-in-context, or drop the code reference from the causal"
                  " sentence.")
        else:
            print("  (Reproduced-in-isolation is NOT confirmed-in-context. Prefer a"
                  " fresh-context falsifier")
            print("   against the actual failing input, upgrading to Confirmed-in-context.)")
        emit_marker(draft_path)
        return 0

    print("BLOCKED by verify-causal-claims: causal claim(s) with no epistemic status.\n",
          file=sys.stderr)
    for lineno, term, line in causal_hits:
        print(f"  line {lineno}: matched '{term}'", file=sys.stderr)
        print(f"            in: {line}", file=sys.stderr)
    print("\nA root-cause claim may not leave your context as bare fact (KTP-907: a synthetic\n"
          "Decimal repro was posted as the confirmed cause of a colleague's 'bug'; the real\n"
          "cause was Altair's 5,000-row cap).\n\nFIX — one of:\n"
          "  1. Have your CALLER dispatch a fresh-context falsifier against the ACTUAL failing\n"
          "     input; it writes an artifact (with `Repro-command:` + `Observed:` lines); add:\n"
          "     Confirmed-in-context: <artifact path>\n"
          "  2. If genuinely still a hypothesis (or an open question), label it honestly:\n"
          "     [HYPOTHESIS — reproduced in isolation, not yet confirmed against the failing"
          " input]\n"
          "  3. If quoting an already-published RCA, say so: 'Per the published RCA (<key>)'.\n"
          "  4. Remove the causal claim (report the observed behavior only).\n\n"
          "Do NOT reword the claim to slip past this gate — the detector is a helper, the rule\n"
          "is the rule.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
