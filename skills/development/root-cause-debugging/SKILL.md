---
name: root-cause-debugging
description: Traces a bug back to the line that first produced the bad state, proves it, and fixes it there. Use for any error, stack trace, failing test, or wrong output before changing code.
---

# Detailed Instructions

Find where the bad value was **created**, not where it was **noticed**, and prove it before
writing a fix. The line in the stack trace is where the program finally tripped over the problem;
the defect is almost always earlier. A fix applied where the error surfaces hides the bug and
moves it somewhere quieter — so no fix is written until the origin has a file, a line, and evidence.

## When to Use

- An exception, stack trace, or crash
- A test that fails (new or previously passing)
- Wrong output: a wrong total, a missing field, a value of the wrong type
- "It worked yesterday" / "it works on my machine"
- A previous fix didn't hold, or the same bug came back

Use it **especially** when the cause looks obvious, when you're under time pressure, or when one
fix has already failed — those are exactly the moments people patch symptoms.

**Don't use when:** the failure is in CI only and the logs haven't been read yet (use
`ci-failure-debugger` first), the test passes and fails at random on the same code (use
`flaky-test-investigator`), or the problem is slowness rather than wrong behavior (use
`performance-investigation`).

## Overview

Most debugging sessions that go wrong skip straight to a fix for the first frame of the stack
trace: a null check, a `try/except`, a type coercion, a default value. The error disappears, the
real defect stays, and it resurfaces later as corrupt data or a different crash. This skill walks
a fixed loop — reproduce, state the symptom precisely, trace backward one hop at a time, confirm
with evidence, fix at the origin, prove it — and stops to question the design when fixes keep
failing.

## Workflow Rules

### Phase 1 — Reproduce

1. **Make it fail on demand** with one command: a single test (`pytest tests/test_x.py::test_y`,
   `npx vitest run -t "name"`), a script, or a `curl`. A bug you can't trigger can't be verified as
   fixed.
2. **If it won't reproduce**, don't guess. Gather evidence instead: exact inputs, logs around the
   failure, environment differences (versions, config, time zone, data), and recent changes
   (`git log --since="3 days ago" --stat`, dependency or config diffs). Reproduce with that.
3. **Read the whole error.** The message, every frame of the stack trace, error codes, and any
   warnings logged before it. The first warning is often the real cause.

### Phase 2 — Trace backward

4. **State the symptom in one sentence:** "`X` is `actual` but should be `expected` at
   `file:line`." Vague symptoms ("checkout is broken") lead to vague fixes.
5. **Walk back one hop at a time.** For the bad value, ask: where was it last assigned or
   computed? Open that location and check whether the value is already bad there. Record each hop:

   ```text
   hop  location             value here        bad?
   1    pricing.py:88        item.price=None   yes
   2    cart.py:41           Item.from_row()   yes
   ```

6. **Stop at the boundary.** The root cause is the first hop where the **inputs are good and the
   output is bad**. That function, line, config entry, or data record is what gets fixed.
7. **At component boundaries, instrument instead of guessing.** When the value crosses a process,
   service, or layer (API → queue → worker, workflow → script → tool), log what enters and leaves
   each boundary once, run it, and let the output show which layer breaks.
8. **Compare with something that works.** Find similar code, an older commit, or a request that
   succeeds, and list every difference — including the ones that "can't matter". `git bisect` is
   the fastest way to find the commit that introduced a regression.

### Phase 3 — Confirm

9. **Form one hypothesis:** "The root cause is X, because Y." Write it down.
10. **Test it with the smallest change:** an assertion at the origin, a log line, or a failing
    test that isolates the defect. Show the output. If it doesn't confirm the hypothesis, form a
    new one — don't stack a fix on an unconfirmed theory.

### Phase 4 — Fix and prove

11. **Write a failing test first** that reproduces the root cause (not just the symptom).
12. **Fix at the origin.** One change. Guards downstream are allowed only *in addition* to the
    real fix, never instead of it. No "while I'm here" refactoring in the same change.
13. **Prove it:** the reproduction from step 1 passes, the new test passes, and the surrounding
    suite still passes.
14. **Remove scaffolding:** temporary logs, prints, and assertions added for investigation.

### When fixes keep failing

15. **Count your attempts.** After two fixes that didn't hold, go back to Phase 2 with what you
    learned. After **three**, stop fixing: each fix revealing a new problem somewhere else means
    the design is the problem (shared mutable state, wrong ownership of data, a race). Say so and
    discuss the design before trying a fourth.

## Checklist

```text
- [ ] Reproduced with a single command (or gathered evidence until I could)
- [ ] Read the full error and any earlier warnings
- [ ] Symptom stated as "X is A but should be B at file:line"
- [ ] Traced backward hop by hop and recorded each hop
- [ ] Root cause = first hop with good inputs and bad output
- [ ] Hypothesis confirmed with evidence (assertion, log, or failing test)
- [ ] Failing test written before the fix
- [ ] One fix, at the origin
- [ ] Reproduction, new test, and suite all pass
- [ ] Debug scaffolding removed
```

## Red Flags

Stop and go back to Phase 2 if you catch yourself thinking:

- "Let me just add a null check here."
- "I'll try changing X and see if the error goes away."
- "It's probably the cache / the framework / a flaky test."
- "I'll change these three things and rerun."
- "I don't fully understand it, but this should work."
- "The error message changed, so we're making progress."
- "One more fix" — after two have already failed.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The cause is obvious from the stack trace." | The trace shows where it crashed, not where the bad value came from. Trace back anyway — it's fast when it really is obvious. |
| "It's an emergency, no time to investigate." | Guess-and-check under pressure is slower and ships a second bug. A backward trace usually takes minutes. |
| "A guard here is harmless." | A guard that swallows the bad value hides the defect and corrupts data downstream. Guard only in addition to the real fix. |
| "I'll write the test after the fix works." | A test written after the fix often passes for the wrong reason. Seeing it fail first proves it tests the bug. |
| "Changing several things at once saves time." | You won't know which change mattered, and you may add a new bug. |
| "It's flaky." | Intermittent bugs have causes too. Prove flakiness by running it many times on the same code. |

## Anti-Patterns (What NOT to do)

* **Editing code before naming a root cause** — you're fixing a guess.
* **Catching and swallowing the exception, or defaulting the value where it surfaced** — the
  error disappears and the corrupt state spreads.
* **Shotgun changes** — several edits at once make it impossible to tell what fixed it.
* **Declaring victory because the error message changed** — only a passing reproduction counts.
* **Blaming the framework, library, or "flakiness" without a hop that shows it** — those claims
  need evidence like any other.
* **Leaving debug prints in the diff** — they leak data and clutter logs.

## Examples

### Example 1: a crash far from its cause

**User:** "Checkout crashes with `TypeError: unsupported operand type(s) for *: 'NoneType' and
'float'` in `pricing.py:88`."

**Expected output:**

```text
## Reproduce
pytest tests/test_checkout.py::test_total_for_new_products → fails with the same TypeError.

## Symptom
item.price is None but should be a float at pricing.py:88 (total += item.price * qty).

## Trace
hop  location          value here                          bad?
1    pricing.py:88     item.price = None                   yes
2    cart.py:41        item built by Item.from_row(row)    yes
3    models.py:112     price = row.get("unit_price")       yes — key missing
4    importer.py:57    supplier CSV header is now "price"  inputs good, output bad  ← root cause

## Hypothesis
The supplier renamed the CSV column "unit_price" → "price" on Nov 2. importer.py maps columns by
the old name, so every product imported since then has price = None.

## Evidence
Temporary assert "unit_price" in row at models.py:112 → fails on 1,204 of 1,204 rows imported
since Nov 2; passes on all older rows.

## Fix (at the origin)
importer.py: accept both "price" and "unit_price"; raise ImportError on rows with neither instead
of storing None. Test added first: test_import_accepts_renamed_price_column (failed, now passes).
Data repair: re-ran the import for Nov 2 onward (1,204 rows updated).

## Verification
Reproduction passes. pytest tests/test_checkout.py tests/test_importer.py → 38 passed.
Temporary assert removed.
```

### Example 2: three fixes in, stop and question the design

**User:** "I've fixed this 'session user is None' bug three times — once in the middleware, once
in the view, once in the template — and it keeps coming back in new places."

**Expected output:**

```text
Three fixes that each move the error somewhere new is the signal to stop patching. That pattern
means the problem is how the session is shared, not any one of those places.

Traced it: request.user is set by AuthMiddleware, but background jobs started from the request
reuse a module-level `current_session` object. When two requests overlap, one request's logout
clears the session the other is still using.

Root cause (design): request-scoped state stored in a module-level global.
Proposal: pass the user explicitly into the background job (job.enqueue(user_id=...)) and delete
the global. That removes the race instead of guarding each place it shows up.

Want me to make that change? It touches 4 call sites; the three earlier guards can then be removed.
```

## Quick Reference

| Situation | Do |
|---|---|
| Error in a stack trace | Trace the bad value backward hop by hop from that frame |
| Can't reproduce | Gather inputs, logs, env diffs, recent changes — don't guess |
| Regression | `git bisect` between a good and bad commit |
| Crosses services or layers | Log in/out at each boundary once, then read |
| Think you know the cause | Prove it with an assertion or failing test first |
| Fix ready | Failing test → one fix at the origin → full suite |
| Two fixes failed | Back to tracing with the new evidence |
| Three fixes failed | Stop; question the design and discuss it |
