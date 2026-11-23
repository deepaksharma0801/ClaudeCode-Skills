---
name: test-plan-writer
description: Writes a risk-based test plan for a change, listing the cases worth testing and at which level. Use when asked what to test, to write tests for a change, or to review test coverage.
---

# Detailed Instructions

Test what can break, at the cheapest level that catches it. A short list of high-value cases
beats exhaustive coverage of the happy path.
Asked to "add tests", models tend to write many near-identical happy-path unit tests that pass
today and catch nothing tomorrow. A risk-based plan spends the effort where bugs actually live.

## When to Use

- "What should I test for this?", "write tests for this PR", "is this well tested?"
- Planning QA for a feature before release
- Reviewing the test coverage of a pull request

**Don't use when:** a test is intermittently failing (use `flaky-test-investigator`), or the task
is refactoring under test (use `safe-refactor`, which writes characterization tests).

## Overview

Asked to "add tests", models tend to write many near-identical happy-path unit tests. This skill
reads the change, identifies what could realistically go wrong, and produces a prioritized plan:
each case with its level (unit, integration, end-to-end), its inputs, and the expected result —
then optionally writes the top cases in the project's existing test style.

## Workflow Rules

1. Read the change (`git diff` against the base branch, or the files the user names) and the
   existing tests for that code. Note the test framework and conventions in use.
2. Summarize the behavior under test in 1–2 sentences.
3. List **risks**: boundaries (empty, zero, max, off-by-one), invalid and malicious input, error
   paths and retries, concurrency and ordering, time zones and dates, permissions, backward
   compatibility, and integrations with external services.
4. For each risk, write a test case: ID, description, level, inputs, expected result, priority
   (P1 must-have / P2 should / P3 nice-to-have).
5. Choose the lowest level that genuinely catches the bug: unit for pure logic, integration for
   database and API contracts, end-to-end only for critical user journeys.
6. Mark which cases are **already covered** by existing tests (with the test name).
7. If asked to write tests, implement P1 cases first, following existing file layout, fixtures,
   and naming. Run them and report results.
8. Call out anything that cannot be tested reliably as written (hidden clock, network calls,
   global state) and suggest the seam that would make it testable.

## Checklist

```text
- [ ] Read the change and existing tests; noted framework and conventions
- [ ] Behavior summarized in 1–2 sentences
- [ ] Risks listed (boundaries, invalid input, errors, concurrency, time, permissions, compat, integrations)
- [ ] Each case: level, inputs, expected result, priority
- [ ] Lowest effective level chosen per case
- [ ] Existing coverage marked with test names
- [ ] P1 tests written in house style and run (if asked)
- [ ] Testability problems named with the seam to add
```

## Red Flags

- Ten happy-path tests that differ only in input values.
- Tests asserting that a mock was called with what the test just passed it.
- "We'll cover it end to end." (for pure logic)
- Tests that depend on `now()`, randomness, or the network.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "More tests = better coverage." | Coverage of risky branches matters; duplicate happy paths add maintenance, not safety. |
| "E2E tests are the most realistic." | They're slow and flaky; use them only for critical journeys and test logic at the unit level. |
| "Mocks make it easy." | Over-mocked tests pass while the real integration breaks. Use real DB/HTTP fakes at the integration level. |

## Anti-Patterns (What NOT to do)

* Do not write tests that only assert a mock was called with the arguments you just passed it.
* Do not pad the plan with trivial getters, setters, or framework behavior.
* Do not default to end-to-end tests for logic a unit test can cover.
* Do not write tests that depend on the current time, random values, or network without controlling them.
* Do not change production code to make a test pass without saying so.
* Do not claim coverage for a case unless a named test actually exercises it.

## Examples

### Example 1: a coupon feature

**User:** "What should I test for this new coupon code feature?" *(diff adds `apply_coupon(cart, code)`)*

**Expected output:**

```text
## Behavior
apply_coupon validates a code, checks expiry and usage limit, and applies a percentage or fixed
discount to the cart subtotal, never below zero.

## Test plan
| ID | Case                                             | Level       | Expected                         | Pri | Covered? |
|----|--------------------------------------------------|-------------|----------------------------------|-----|----------|
| C1 | 20% coupon on $50 cart                           | unit        | subtotal $40                     | P1  | yes — test_percent_coupon |
| C2 | $15 fixed coupon on $10 cart                     | unit        | subtotal $0, not -$5             | P1  | no |
| C3 | Code expired 1 second ago (frozen clock)         | unit        | CouponExpired, cart unchanged    | P1  | no |
| C4 | Usage limit reached (limit 100, used 100)        | integration | CouponExhausted                  | P1  | no |
| C5 | Two concurrent redemptions of last remaining use | integration | exactly one succeeds             | P1  | no |
| C6 | Lowercase / padded code " save20 "               | unit        | treated as SAVE20                | P2  | no |
| C7 | Coupon applied twice to same cart                | unit        | second call rejected             | P2  | no |
| C8 | Checkout total with coupon end-to-end            | e2e         | charged amount matches cart      | P3  | no |

## Testability notes
- apply_coupon calls datetime.now() directly; inject a clock to make C3 deterministic.
- C5 needs a real database transaction; the usage check is currently read-then-write (race).
```

### Example 2: reviewing a PR's tests

**User:** "Is this PR tested enough? It adds CSV export for invoices."

**Expected output:**

```text
Existing tests in the PR: 3, all happy path (10 invoices → 11 lines).

Missing, by risk:
| ID | Case                                              | Level       | Pri |
|----|---------------------------------------------------|-------------|-----|
| E1 | Field containing comma, quote, or newline is quoted correctly | unit | P1 |
| E2 | Cell starting with = + - @ is escaped (CSV injection in Excel) | unit | P1 |
| E3 | User from org A can't export org B's invoices      | integration | P1 |
| E4 | 0 invoices → header row only, not an error         | unit        | P2 |
| E5 | 100k invoices streams without loading all into memory | integration | P2 |
| E6 | Non-ASCII names survive (UTF-8 with BOM for Excel) | unit        | P3 |

Verdict: not enough — E1–E3 are must-haves before merge (E2 and E3 are security issues).
```

## Quick Reference

| Risk | Typical case |
|---|---|
| Boundaries | empty, zero, one, max, max+1 |
| Invalid input | wrong type, missing field, malicious string |
| Errors | dependency down, timeout, partial failure, retry |
| Time | frozen clock, time zones, DST, month end |
| Concurrency | two requests for the last unit |
| Permissions | other user's / other tenant's object |
| Level | unit for logic, integration for DB/API contracts, e2e for critical journeys |
