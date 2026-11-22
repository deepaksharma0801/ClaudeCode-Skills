---
name: root-cause-debugging
description: Traces a bug back to the line that first produced the bad state before changing any code. Use when an error, stack trace, or wrong output appears and the cause is not obvious.
---

# Detailed Instructions

Find where the bad value was *created*, not where it was *noticed*. No fix is written until the
origin is named, with a file and line.

## Overview

Most failed debugging sessions patch the first frame of the stack trace: add a null check, wrap a
try/except, coerce a type. The error goes away and the real defect moves somewhere quieter. This
skill forces a backward trace from the symptom to the first point where state went wrong, then
fixes it there.

## Workflow Rules

1. **Reproduce first.** Get the failure to happen on demand with a single command (a test, a
   script, a curl). If it cannot be reproduced, say so and gather evidence (logs, inputs) before
   touching code.
2. **State the symptom precisely.** Write one sentence: *"`X` is `actual` but should be
   `expected` at `file:line`."*
3. **Walk backward one hop at a time.** For the bad value, ask: where was it last assigned? Open
   that location. Repeat. At each hop, record `file:line — value here — still bad? yes/no`.
4. **Stop at the boundary.** The origin is the first hop where inputs are good and the output is
   bad. That function, line, or config entry is the root cause.
5. **Confirm with evidence.** Add a temporary log or assertion at the origin, or write a failing
   test that isolates it. Show the output.
6. **Fix at the origin.** Change the code where the bad state is created. Guards further
   downstream are allowed only in addition to that fix, never instead of it.
7. **Prove it.** Rerun the reproduction from step 1, and the surrounding test suite.
8. **Remove scaffolding.** Delete temporary logs and prints before finishing.

## Anti-Patterns (What NOT to do)

* Do not edit code before step 4 names a root cause.
* Do not "fix" by catching and swallowing the exception, or adding a default value where the error
  surfaced.
* Do not change several things at once and see if the error disappears. One hypothesis, one change.
* Do not declare victory because the error message changed. The reproduction must pass.
* Do not blame the framework, the library, or "flakiness" without a hop in the trace that shows it.
* Do not leave debug prints in the final diff.

## Examples

**User:** "Checkout crashes with `TypeError: unsupported operand type(s) for *: 'NoneType' and
'float'` in `pricing.py:88`."

**Expected output:**

```text
## Symptom
`item.price` is None but should be a float at pricing.py:88 (`total += item.price * qty`).

## Trace
1. pricing.py:88       — item.price = None              — bad
2. cart.py:41          — item built by Item.from_row()  — bad
3. models.py:112       — price = row.get("unit_price")  — bad (key missing)
4. importer.py:57      — CSV header renamed "unit_price" → "price" on 2026-11-02 — inputs good, output bad

## Root cause
importer.py:57 maps CSV columns by a hard-coded name that no longer matches the supplier feed.
Every product imported since the rename has price = None.

## Evidence
Added `assert "unit_price" in row` at models.py:112 → fails on 1,204 of 1,204 new rows.

## Fix
importer.py: map both "price" and "unit_price", and raise on rows with no price instead of
storing None. Added test_import_accepts_renamed_price_column.

## Verification
pytest tests/test_checkout.py tests/test_importer.py → 38 passed. Debug assert removed.
```
