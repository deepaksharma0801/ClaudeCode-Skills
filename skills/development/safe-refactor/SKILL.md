---
name: safe-refactor
description: Refactors code in small, behavior-preserving steps, pinning current behavior with tests first. Use when asked to refactor, clean up, restructure, or untangle code without changing what it does.
---

# Detailed Instructions

A refactor changes structure, never behavior. Prove behavior is pinned before the first edit, and
keep the code working after every step.

## Overview

Large "rewrite it cleaner" passes are where regressions hide: behavior changes slip in next to
renames, and nobody can review a 900-line diff. This skill pins existing behavior, then moves in
small named steps (extract, rename, inline, move), running tests after each one.

## Workflow Rules

1. **State the goal** in one sentence (e.g. "split `OrderService` so pricing can be tested alone")
   and the scope: which files may change.
2. **Pin behavior.** Find the tests that cover the code. If coverage is thin, write
   characterization tests first: call the code with realistic inputs and assert on its *current*
   output — including odd results — and commit or stash them separately.
3. **Run the tests** and confirm they pass before touching anything. If they already fail, stop
   and report it; do not refactor on a red suite.
4. **Plan the steps** as a short list of standard moves: extract function, rename, inline
   variable, move module, introduce parameter object, replace conditional with lookup.
5. **One step at a time.** Make a single move, run the tests, continue only when green. If a step
   goes red, undo that step rather than patching forward.
6. **Keep public interfaces stable** unless the user agreed to change them; when they change,
   update every call site in the same step.
7. **Separate behavior fixes.** If you find a bug, note it and keep the buggy behavior (the
   characterization test documents it). Fix it in a separate change after the refactor.
8. **Report** the steps taken, the test command and result, and any bugs found but not fixed.

## Anti-Patterns (What NOT to do)

* Do not start editing before running the tests.
* Do not mix refactoring with new features, bug fixes, or formatting-only churn across unrelated files.
* Do not delete or weaken a test to make a refactor pass.
* Do not do the whole refactor in one giant edit and test only at the end.
* Do not rename public APIs, config keys, or database columns as part of a "cleanup" without asking.
* Do not claim "no behavior change" if the tests do not cover the changed paths — say what is unverified.

## Examples

**User:** "This `process_order` function is 300 lines. Clean it up."

**Expected output:**

```text
## Goal
Break process_order (orders.py:40–340) into named steps without changing behavior.
Scope: orders.py, tests/test_orders.py.

## Behavior pinned
Existing tests cover 2 of 5 branches. Added 6 characterization tests (tax-exempt, multi-currency,
zero-quantity line, coupon + sale price, backorder, invalid region). All 14 pass on the original code.

## Steps (tests green after each)
1. Extract validate_order()            — 14 passed
2. Extract compute_line_totals()       — 14 passed
3. Extract apply_discounts()           — 14 passed
4. Replace region if/elif chain with TAX_RATES lookup — 14 passed
5. Inline 4 single-use temporaries     — 14 passed

process_order is now 38 lines calling 4 helpers. Public signature unchanged.

## Found, not fixed
- Zero-quantity lines still get a shipping charge (pinned by test_zero_quantity_line).
  Recommend fixing in a separate change.
```
