---
name: flaky-test-investigator
description: Finds why a test passes sometimes and fails other times by reproducing the flake and classifying its cause. Use when a test fails intermittently in CI, or passes locally but fails in CI.
---

# Detailed Instructions

A flaky test is a real bug — in the test or the code — until proven otherwise. Reproduce the
failure reliably before fixing it, and never "fix" a flake with a retry or a longer sleep alone.

## Overview

Flaky tests erode trust in the whole suite: people rerun CI until it is green and stop reading
failures. This skill reproduces the flake by running the test many times under varying conditions,
classifies the cause into a known category, and fixes the root cause so the test is deterministic.

## Workflow Rules

1. **Collect evidence:** recent failure logs, the error message, failure rate (from CI history if
   available), and whether it fails alone or only with other tests.
2. **Reproduce** by running the test repeatedly:
   - Alone, many times: `pytest -x --count=100 test_x.py::test_y` (pytest-repeat),
     `go test -run TestY -count=200 -race`, `jest -t "name" --runInBand` in a loop.
   - In random order or with its neighbors: `pytest -p random_order`, `jest --randomize`,
     `rspec --order random --seed <seed from CI>`.
   - Under CI-like conditions: parallel workers, limited CPU, the CI time zone and locale.
3. **Classify** the cause:

   | Category | Typical signs |
   |---|---|
   | Order dependence / shared state | Fails only after certain tests; globals, singletons, DB rows not cleaned up |
   | Timing / async | Sleeps, polling without a condition, animation, missing `await` |
   | Time and date | Uses `now()`; fails near midnight, month end, DST, or in another time zone |
   | Randomness | Unseeded random data, unordered set/dict iteration, UUID ordering |
   | Concurrency | Data races, parallel workers sharing ports, files, or DB schemas |
   | External dependency | Real network calls, third-party APIs, DNS |
   | Resource limits | Timeouts on slow CI machines, memory, file descriptors |

4. **Fix the cause**, matching the category: isolate state (fixtures, transactions rolled back per
   test), wait for a condition instead of sleeping, inject or freeze the clock, seed randomness and
   sort before comparing, use unique ports and temp dirs per worker, stub the network.
5. **Prove it:** run the same repetition that reproduced the failure; report the before/after
   failure rate (e.g. 7/200 → 0/500).
6. If the bug is in the product code (a real race), say so — the test was right.

## Anti-Patterns (What NOT to do)

* Do not add retries, `@flaky`, or longer timeouts as the only fix.
* Do not mark the test skipped without an issue link and an owner.
* Do not declare it fixed after one green run.
* Do not replace `sleep(1)` with `sleep(5)`.
* Do not assume the test is wrong; intermittent failures often expose real race conditions.

## Examples

**User:** "`test_invoice_due_dates` fails maybe once a week in CI. Can't reproduce locally."

**Expected output:**

```text
## Evidence
CI failures: 4 in the last 30 days, all between 23:00 and 00:30 UTC.
Error: AssertionError: assert date(2026, 12, 1) == date(2026, 11, 30)

## Reproduction
Alone, 200 runs locally (Pacific time): 0 failures.
With the clock frozen at 2026-11-30T23:30Z (time-machine): fails 200/200.

## Cause — Time and date
The test builds the expected due date with date.today() (local time), while
invoice.due_date uses datetime.now(timezone.utc).date(). Between 23:00 and midnight UTC on CI
(and at other hours in other zones) the two disagree by one day.

## Fix
- Test: freeze time with @time_machine.travel("2026-11-30T23:30Z") and compute the
  expected value from the frozen UTC date.
- Code: invoices/service.py:52 already uses UTC (correct). No product change needed.

## Proof
Swept the frozen clock across every hour of 3 days, including month end: 0 failures in 72 cases.
```
