---
name: safe-refactor
description: Refactors code in small, behavior-preserving steps, pinning current behavior with tests first. Use when asked to refactor, clean up, restructure, rename, split, or untangle code.
---

# Detailed Instructions

A refactor changes structure, never behavior. Prove the current behavior is pinned by tests before
the first edit, then move in small named steps with the tests green after every one. When a step
goes red, undo that step — don't patch forward — because a refactor that needs debugging has
stopped being a refactor.

## When to Use

- "Clean this up", "this function is too long", "untangle this module"
- Extracting, renaming, moving, or splitting code
- Preparing code for a feature ("make room before adding X")
- Removing duplication across files

**Don't use when:** the user wants behavior to change (that's a feature or a bug fix — do it as a
separate change, before or after the refactor), or the code is being deleted and replaced wholesale
(write tests against the new code instead).

## Overview

Big "rewrite it cleaner" passes are where regressions hide: a behavior change slips in next to
fifty renames and nobody can review the diff. This skill pins existing behavior — including odd
behavior — with characterization tests, plans a sequence of standard refactoring moves, applies
them one at a time with tests between each, and keeps any bug it finds out of the refactor so the
diff stays behavior-neutral and reviewable.

## Workflow Rules

### Phase 1 — Scope and pin

1. **State the goal and the boundary** in two lines: what structural outcome you want ("pricing
   logic testable without a database") and which files may change. Anything outside that list is
   out of scope.
2. **Find the tests that cover the code.** Run them with coverage on just this area
   (`pytest --cov=orders --cov-report=term-missing tests/test_orders.py`,
   `npx vitest run --coverage src/orders`). Uncovered branches are unprotected.
3. **Write characterization tests for the gaps.** Call the code with realistic inputs and assert on
   what it returns **today**, including results that look wrong. Name them for what they pin
   (`test_zero_quantity_line_still_charges_shipping`). Commit them separately, before any refactor
   commit, so reviewers can see behavior was pinned first.
4. **Run the suite and confirm it's green.** If it's already red, stop and report it — refactoring
   on a failing suite makes every later failure ambiguous.

### Phase 2 — Plan the moves

5. **List the steps as standard, named moves**, each small enough to review in a minute:
   extract function, inline variable, rename, move to module, introduce parameter object, replace
   conditional with lookup table, split loop, replace temp with query, extract class.
6. **Order them so each leaves the code working.** Renames and extractions first; moves across
   modules after; deletions of dead code last.

### Phase 3 — Execute

7. **One move at a time.** Make it, run the tests for the area, continue only when green. Prefer
   the editor's or language server's automated refactorings (rename symbol, extract method) over
   hand edits — they update every reference.
8. **When a step goes red, revert that step** (`git checkout -- <file>` or `git stash`) and try a
   smaller one. Don't fix forward.
9. **Commit after every few green steps** with a message naming the move
   (`Extract compute_line_totals from process_order`). Small commits make bisecting and reviewing easy.
10. **Keep public interfaces stable** — function signatures, API routes, config keys, database
    columns, event names — unless the user agreed to change them. If one must change, update every
    caller in the same step and search the whole repo (and other repos that import it) for usages.

### Phase 4 — Separate and report

11. **Don't fix bugs inside the refactor.** If you find one, note it, leave the pinned behavior in
    place, and propose fixing it as its own change afterward. Mixing the two makes the refactor
    unreviewable and the fix untraceable.
12. **Report** the moves made, the test command and result after the last step, before/after size
    or complexity if useful, bugs found but not fixed, and anything not covered by tests.

## Checklist

```text
- [ ] Goal and file boundary stated
- [ ] Coverage checked for the area
- [ ] Characterization tests added for uncovered behavior, committed first
- [ ] Suite green before any change
- [ ] Moves planned as a named list
- [ ] One move at a time, tests green after each
- [ ] Red step reverted, not patched
- [ ] Public interfaces unchanged (or every caller updated)
- [ ] Bugs found are noted, not fixed in this change
- [ ] Final report with test result and anything unverified
```

## Red Flags

- "While I'm in here, I'll also fix…"
- "I'll run the tests once at the end."
- "This rename is safe; it's only used here." (Did you search?)
- "The test was testing the old structure, so I deleted it."
- "It's failing now but I know why; one more edit."
- A diff where reviewers can't tell which lines changed behavior.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The code is simple, it doesn't need tests first." | Simple code has callers depending on its quirks. Characterization tests take minutes and catch them. |
| "Doing it in one pass is faster." | One big pass is fast until a test fails and you can't tell which of forty edits caused it. |
| "I'll fix this obvious bug since I'm here." | A behavior change inside a refactor can't be reviewed or reverted on its own. Fix it next. |
| "The old test was coupled to the implementation." | Then rewrite it to test behavior through the public interface — don't delete it. |
| "Coverage is good enough." | Coverage shows lines executed, not branches asserted. Check the branches you're about to move. |

## Anti-Patterns (What NOT to do)

* **Editing before running the tests** — you can't tell pre-existing failures from new ones.
* **Mixing refactoring with features, bug fixes, or repo-wide formatting** — the diff stops being reviewable.
* **Deleting or weakening a test to make a refactor pass** — that test was the safety net.
* **One giant edit, tested at the end** — failures can't be localized.
* **Renaming public APIs, config keys, or columns as "cleanup" without agreement** — breaks callers you can't see.
* **Claiming "no behavior change" for paths no test covers** — say what's unverified instead.

## Examples

### Example 1: a 300-line function

**User:** "This `process_order` function is 300 lines. Clean it up."

**Expected output:**

```text
## Goal
Split process_order (orders.py:40–340) into named steps without changing behavior.
Boundary: orders.py, tests/test_orders.py.

## Behavior pinned
Coverage: 2 of 5 branches tested. Added 6 characterization tests (tax-exempt customer,
multi-currency, zero-quantity line, coupon + sale price, backorder, invalid region).
All 14 tests pass on the original code. Committed: "Pin process_order behavior with tests".

## Moves (tests after each)
1. Extract validate_order()                               14 passed
2. Extract compute_line_totals()                          14 passed
3. Extract apply_discounts()                              14 passed
4. Replace region if/elif chain with TAX_RATES lookup     14 passed
5. Inline 4 single-use temporaries                        14 passed

process_order is now 38 lines calling 4 helpers. Signature unchanged; 3 callers untouched.

## Found, not fixed
Zero-quantity lines still get a shipping charge (pinned by
test_zero_quantity_line_still_charges_shipping). Suggest fixing in a separate PR.
```

### Example 2: a rename that crosses a boundary

**User:** "Rename `get_usr` to `get_user` everywhere."

**Expected output:**

```text
Search: 41 references in this repo (rename-symbol via the language server), plus:
- `get_usr` is exported from the public package `acme_client` (acme_client/__init__.py:12)
- 2 other repos import it (billing-service, admin-tools — GitHub code search)

Plan:
1. Rename to get_user in this repo (all 41 references, one commit). Tests: 512 passed.
2. Keep a deprecated alias so external callers don't break:
   def get_usr(*args, **kwargs):
       warnings.warn("get_usr is deprecated; use get_user", DeprecationWarning, stacklevel=2)
       return get_user(*args, **kwargs)
3. Remove the alias in the next major release, after billing-service and admin-tools migrate.
```

## Quick Reference

| Situation | Do |
|---|---|
| Before touching code | Check coverage, add characterization tests, confirm green |
| Planning | Named moves, smallest first, each leaves code working |
| Each step | One move → run tests → continue only if green |
| Step goes red | Revert it; try a smaller step |
| Found a bug | Note it, keep behavior, fix separately |
| Public name must change | Update all callers; add a deprecated alias for external ones |
| Done | Report moves, test result, unverified paths |
