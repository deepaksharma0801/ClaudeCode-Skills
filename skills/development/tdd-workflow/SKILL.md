---
name: tdd-workflow
description: Builds features and fixes bugs test-first in red-green-refactor cycles, watching each test fail before coding. Use when asked for TDD or to fix a bug with a regression test.
---

# Detailed Instructions

Write one failing test, **run it and watch it fail for the right reason**, write the least code
that makes it pass, then refactor with the suite green. Repeat in small steps. A test you never
saw fail proves nothing: it may not run, may assert the wrong thing, or may already pass. And
code written before its test tends to get tests shaped around the code rather than around the
behavior.

## When to Use

- "Use TDD" / "write the tests first"
- Adding behavior with clear inputs and outputs: parsers, pricing rules, validators, state machines
- Fixing a bug: reproduce it with a failing test before touching the code
- Changing code with tricky edge cases where regressions are likely

**Don't use when:** exploring an unknown API or prototyping UI layout (spike first, then test the
kept design), changing structure without changing behavior (use `safe-refactor`), or deciding
*what* to test across levels (use `test-plan-writer`).

## Overview

The common failure is "TDD-shaped" work: code first, tests after, all passing on the first run.
That skips the step that gives TDD its value — confirming the test can fail. This skill runs
strict cycles: list behaviors, pick the simplest, write a test, see it fail with the expected
message, make it pass minimally, refactor, commit. Bugs start with a reproducing test.

## Workflow Rules

### 1. List behaviors

1. Write a short test list of behaviors (not methods): "free shipping over $50", "no free
   shipping for gift cards", "rounds to cents". Start with the simplest; keep adding cases as you
   discover them.

### 2. Red

2. Write **one** test for one behavior, using the public interface, with a name that states the
   behavior (`test_orders_over_50_ship_free`).
3. **Run it. It must fail, and for the expected reason** — an assertion about the behavior, not
   an import error or typo. If it passes, the behavior already exists or the test is wrong;
   find out which before going on.

### 3. Green

4. Write the **minimum** code to pass, even if it looks naive. Run the test and the whole
   relevant suite.
5. Don't add behavior no test asked for. If you think of a case, add it to the test list.

### 4. Refactor

6. With everything green, clean up names, duplication, and structure in both code and tests.
   Run the suite after each change. Never refactor on red.
7. Commit at green: small commits make bisecting and reviewing easy.

### 5. Bugs

8. For a bug: write a test that reproduces the report, see it fail with the buggy result, fix,
   and see it pass. That test stays as the regression guard.

## Checklist

```text
- [ ] Test list of behaviors written
- [ ] One test at a time, named for the behavior
- [ ] Watched it fail for the expected reason
- [ ] Minimal code to pass; whole suite green
- [ ] Refactored only on green; ran tests after each step
- [ ] Committed at green
- [ ] Bug fixes start with a failing reproduction
```

## Red Flags

- Writing the implementation, then "adding tests".
- A new test that passes on its first run and nobody asks why.
- Five tests written before running any.
- Mocking the unit under test, or asserting on private internals.
- Refactoring while a test is red.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll write the test right after." | Tests written after get shaped around the code and rarely fail first. |
| "It's too simple to test first." | Simple tests take a minute and catch the off-by-one you didn't expect. |
| "Seeing it fail is a formality." | It's the only proof the test can detect the bug. |
| "Faster to write all the tests up front." | Then you debug many failures at once and lose the small steps. |

## Anti-Patterns (What NOT to do)

* **Testing implementation details** — tests break on refactors and don't protect behavior.
* **Over-mocking** — tests pass while the real integration is broken.
* **Writing more code than the test requires** — untested behavior sneaks in.
* **Skipping refactor** — TDD without refactor leaves naive code in place.
* **Huge steps** — if a cycle takes over ~15 minutes, the step is too big; split the behavior.

## Examples

### Example 1: a shipping rule, cycle by cycle

**User:** "Use TDD to add free shipping for orders of $50 or more, except gift cards."

**Expected output:**

```text
Test list: under $50 pays $5.99 · $50.00 exactly ships free · gift-card-only orders pay shipping
· mixed cart: gift cards don't count toward $50.

Cycle 1 — RED
  def test_orders_under_50_pay_standard_shipping():
      assert shipping_cost(Cart([item(49.99)])) == Decimal("5.99")
  $ pytest -q tests/test_shipping.py
  E  NameError: name 'shipping_cost' is not defined      <- wrong reason; add an empty stub
  E  assert None == Decimal('5.99')                       <- right reason
GREEN: return Decimal("5.99")    → 1 passed

Cycle 2 — RED
  def test_orders_of_50_ship_free():
      assert shipping_cost(Cart([item(50.00)])) == Decimal("0")
  E  assert Decimal('5.99') == Decimal('0')
GREEN: return Decimal("0") if cart.total >= 50 else Decimal("5.99")    → 2 passed

Cycle 3 — RED: mixed cart [gift_card(40), item(15)] expects 5.99 → fails with 0
GREEN: sum only non-gift-card items toward the threshold → 3 passed
REFACTOR: extract FREE_SHIPPING_THRESHOLD and eligible_total(); suite green → commit.
```

### Example 2: a bug report

**User:** "Discount codes sometimes apply twice. Fix it."

**Expected output:**

```text
First reproduce it as a test, before reading the fix-candidate code:
  def test_applying_same_code_twice_applies_once():
      cart = Cart([item(100)])
      cart.apply_code("SAVE10"); cart.apply_code("SAVE10")
      assert cart.total == Decimal("90.00")
  E  assert Decimal('80.00') == Decimal('90.00')      <- reproduces the report
Fix: make apply_code idempotent per code (store applied codes in a set).
  → passes; full suite green. The test stays as the regression guard.
```

## Quick Reference

| Phase | Do | Check |
|---|---|---|
| List | Behaviors, simplest first | Add new cases as found |
| Red | One behavior test | Fails for the expected reason |
| Green | Minimum code | Whole suite passes |
| Refactor | Clean code and tests | Green after each change |
| Commit | At green | Small and bisectable |
| Bug | Reproducing test first | Fails with the bug, then passes |
