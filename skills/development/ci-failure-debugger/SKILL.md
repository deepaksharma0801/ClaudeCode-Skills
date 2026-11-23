---
name: ci-failure-debugger
description: Diagnoses failing CI runs (GitHub Actions, GitLab CI, CircleCI) from logs, finds the first real error, and fixes the cause. Use when a pipeline fails or passes locally but not in CI.
---

# Detailed Instructions

Read the log from the first failure, not the last line. CI output buries the cause under cascading
errors, and the fix is almost always about what differs between CI and the developer's machine.
Rerunning until green is not a fix: it hides a real defect or a flaky test that will fail again at
the worst moment, and it trains the team to ignore red builds.

## When to Use

- A red build, test, lint, or deploy job in GitHub Actions, GitLab CI, CircleCI, Jenkins, Buildkite
- "Passes locally but fails in CI"
- A pipeline that started failing without code changes (dependency, image, or runner drift)
- Deploy jobs failing on secrets, permissions, or environment configuration

**Don't use when:** the failure is a test that passes and fails on the same commit (use
`flaky-test-investigator` once you've confirmed that), or the failing test also fails locally with
a clear code error (use `root-cause-debugging`).

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

## Checklist

```text
- [ ] Pulled the failed job's log (gh run view --log-failed / job log)
- [ ] Found the first real error, not the last line
- [ ] Classified it (code, env drift, dependency drift, cache, secrets, resources, flaky, config)
- [ ] Compared CI and local: runtime, package manager, OS image, env vars, exact command
- [ ] Reproduced locally with CI's command and versions (or the CI image)
- [ ] Smallest fix made and pushed
- [ ] Job passes on the fix commit (flaky claims shown with pass + fail on one commit)
```

## Red Flags

- "Just rerun it."
- "The error says exit code 1, so the test runner is broken."
- "Let's add `continue-on-error: true` for now."
- "I'll bump all the dependencies, that usually fixes it."
- "Let me echo the secret to see if it's set."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "It's probably flaky." | Prove it: the same commit must both pass and fail. Most "flaky" CI failures are environment drift. |
| "It works on my machine, so CI is wrong." | CI is a cleaner environment; it usually exposes a real dependency on your local setup (time zone, cached files, global tools). |
| "Skipping this test unblocks the release." | It ships the bug the test was catching, and nobody re-enables it. |
| "The last error in the log is the cause." | It's usually a consequence. Scroll up to the first failure. |

## Anti-Patterns (What NOT to do)

* Do not rerun until green and call it fixed.
* Do not quote the last error in the log as the cause without checking what happened before it.
* Do not "fix" CI by skipping tests, adding `continue-on-error`, or deleting the failing step.
* Do not print or echo secret values to debug a secrets problem; check whether the variable is set.
* Do not upgrade every dependency to fix one failure.

## Examples

### Example 1: passes locally, fails in CI

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

### Example 2: a failure with no code change

**User:** "Nothing changed in our repo but the build broke overnight."

**Expected output:**

```text
$ gh run list --workflow build.yml --limit 5
✓ build  main  Nov 21 (abc123)
X build  main  Nov 22 (abc123)   ← same commit, so the change is outside the repo

$ gh run view <failed-run-id> --log-failed   (trimmed)
  Run actions/setup-python@v5  python-version: 3.x
  Successfully set up CPython (3.14.0)
  ...
  ERROR: Could not build wheels for numpy==1.26.4

## First real error
numpy 1.26.4 has no wheel for Python 3.14, so pip tries to compile it and fails.

## Category: Environment drift
The workflow asks for `python-version: 3.x`, which now resolves to a newer Python than yesterday.

## Fix
Pin the version CI should use and keep it in one place:
  .python-version → 3.12
  setup-python: python-version-file: .python-version
Re-ran on the same commit: passes.

Follow-up (separate PR): test against the newer Python in an additional matrix entry before
moving to it.
```

## Quick Reference

| Log shows | Likely category | First move |
|---|---|---|
| Same commit passed before | Drift (runtime, image, dependency) | Diff versions between the passing and failing run |
| `exit code 137` / `Killed` | Out of memory | Reduce parallelism or raise runner memory |
| 401/403, empty env var | Secrets/permissions | Check fork-PR secret rules and `permissions:` |
| Passes after cache clear | Stale cache | Include the lockfile hash in the cache key |
| Different test fails each run | Flaky / order-dependent | Run with the CI seed; see flaky-test-investigator |
| YAML or "unknown input" errors | Workflow config | Validate the workflow file and action inputs |

