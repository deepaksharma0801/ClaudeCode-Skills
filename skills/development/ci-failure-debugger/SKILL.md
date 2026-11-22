---
name: ci-failure-debugger
description: Diagnoses failing CI runs (GitHub Actions, GitLab CI, CircleCI) from logs, finds the first real error, and fixes the cause. Use when a pipeline fails or passes locally but not in CI.
---

# Detailed Instructions

Read the log from the first failure, not the last line. CI output buries the cause under cascading
errors, and the fix is almost always about what differs between CI and the developer's machine.

## Overview

When CI goes red, people rerun it, or patch the final error message ("exit code 1"). This skill
pulls the failed job's log, locates the first meaningful error, classifies the failure, compares the
CI environment with local, and proposes the smallest fix — or proves the failure is flaky and hands
off to a deeper investigation.

## Workflow Rules

1. **Get the failing log**, scoped to failed steps:
   - GitHub Actions: `gh run list --limit 5`, then `gh run view <run-id> --log-failed`
     (or `gh pr checks` on a PR).
   - GitLab: `glab ci view` / the job's raw log. CircleCI: the step output or API.
2. **Find the first real error:** search upward from the failure for the earliest `error`,
   `Error:`, `FAILED`, `fatal`, `Traceback`, or non-zero exit. Ignore warnings and errors that are
   consequences of an earlier one.
3. **Classify it:**

   | Category | Typical signs | Usual fix |
   |---|---|---|
   | Real code / test failure | assertion or compile error that also fails locally | fix the code |
   | Environment drift | different runtime version, OS, locale, time zone | pin versions in the workflow (`setup-node` `node-version`, `.tool-versions`) |
   | Dependency drift | lockfile missing or ignored, new transitive release | commit the lockfile, use `npm ci` / `pip install -r` with hashes / `--frozen-lockfile` |
   | Cache problems | passes after cache clear; stale build artifacts | fix the cache key (include the lockfile hash) |
   | Secrets / permissions | empty env var, 401/403, `Resource not accessible by integration` | secrets are not passed to workflows from forked PRs; set `permissions:` for the `GITHUB_TOKEN` |
   | Resource limits | killed, exit 137, OOM, timeouts | reduce parallelism, raise memory, split the job |
   | Flaky / order-dependent | passes on rerun, different test each time | do not just rerun; see the flaky-test-investigator skill |
   | Workflow config | YAML error, wrong `if:`, path filters, missing `needs:` | fix the workflow file |

4. **Compare environments:** runtime and package-manager versions, OS image, env vars, and the
   exact command CI runs (copy it from the workflow file, not from memory).
5. **Reproduce locally** with the same command and versions. Use the CI container image
   (`docker run` with the job's image) or `act` for GitHub Actions when the environment matters.
6. **Fix and verify:** make the smallest change, push, and confirm the job passes. For flaky
   failures, show it failing and passing on the same commit before calling it flaky.
7. **Report** the first error (quoted, trimmed), the category, the root cause, and the fix.

## Anti-Patterns (What NOT to do)

* Do not rerun until green and call it fixed.
* Do not quote the last error in the log as the cause without checking what happened before it.
* Do not "fix" CI by skipping tests, adding `continue-on-error`, or deleting the failing step.
* Do not print or echo secret values to debug a secrets problem; check whether the variable is set.
* Do not upgrade every dependency to fix one failure.

## Examples

**User:** "CI is failing on my PR but tests pass locally."

**Expected output:**

```text
$ gh pr checks
test (ubuntu-latest, node 20)   fail
lint                            pass

$ gh run view 9182736455 --log-failed   (trimmed)
  npm ci
  ...
  FAIL src/utils/date.test.ts
    formatDueDate › shows the local date
      Expected: "Nov 30"
      Received: "Dec 1"
  Error: Process completed with exit code 1.

## First real error
src/utils/date.test.ts — formatDueDate expected "Nov 30", got "Dec 1".

## Category: Environment drift (time zone)
Your machine runs in America/Los_Angeles; GitHub runners use UTC. The test builds a date at
23:30 local time and formats it with the system zone, so it rolls over to the next day in UTC.

## Reproduce
TZ=UTC npm test -- src/utils/date.test.ts   → fails locally the same way

## Fix
- Make the test independent of the machine: pass timeZone: "America/Los_Angeles" explicitly to
  formatDueDate in the test, matching the product behavior.
- Optional guard: set TZ=UTC in the npm test script so local runs match CI.

Pushed; test job passes (run 9182740012).
```
