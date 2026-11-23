---
name: security-finding-triage
description: Triages static analysis findings (Semgrep, CodeQL, Bandit, Snyk Code) by tracing source to sink to decide true or false positive, severity, and fix. Use for any scanner report.
---

# Detailed Instructions

Every finding gets a verdict backed by a traced data flow: where the value comes from, what
happens to it on the way, and where it ends up. Severity comes from exploitability in this
codebase, not from the scanner's default label.
Scanners over-report; teams that can't separate the real bugs from noise end up ignoring the whole
report. A traced verdict per finding — and a documented suppression for false positives — keeps
the next scan meaningful.

## When to Use

- A Semgrep, CodeQL, Bandit, SonarQube, Snyk Code, or Checkmarx report to review
- GitHub code scanning alerts piling up
- Deciding whether to suppress or fix a specific finding
- A security gate failing a PR

**Don't use when:** the findings are dependency CVEs (use `dependency-audit`), or headers/config
(use `security-headers-check`).

## Overview

Scanners over-report: a "SQL injection" on a query built from a constant, a "hard-coded secret"
that is a test fixture. Teams then ignore the whole report, including the real bug. This skill
groups findings, traces each candidate from source to sink, classifies it, assigns a severity
that reflects reachability and impact, and proposes a fix or a documented suppression.

## Workflow Rules

1. **Load the report** (SARIF, JSON, or text) and group findings by rule. Duplicates of one root
   cause (the same helper called in 30 places) are triaged once, at the helper.
2. **For each group, trace the flow:**
   - **Source:** where does the value come from — HTTP request, file, environment, database, a
     constant? Is it attacker-controlled?
   - **Path:** validation, encoding, parameterization, type conversion, or allow-listing between
     source and sink. Is it applied on *every* path?
   - **Sink:** what the value reaches — SQL, shell, file path, HTML, redirect, deserializer,
     template, crypto API.
   - **Reachability:** is the code reachable in production (not dead code, test-only, or behind
     an admin-only path)?
3. **Classify:** `TRUE POSITIVE`, `FALSE POSITIVE` (state exactly why: constant input,
   parameterized, sanitized, unreachable), or `NEEDS INFO` (what is unknown).
4. **Severity** for true positives: based on attacker access (unauthenticated > authenticated >
   admin), impact (data exposure, code execution, account takeover), and ease of exploitation.
   Say when it differs from the scanner's label and why.
5. **Fix** true positives at the root: parameterized queries, argument arrays instead of shell
   strings, path normalization plus base-directory checks, context-aware output encoding,
   allow-listed redirects, safe deserializers. Add a test that would have caught it.
6. **Suppress** false positives in code with a reason, so the next scan stays clean and reviewers
   can audit the decision: Semgrep `# nosemgrep: <rule-id>`, Bandit `# nosec B608`, CodeQL —
   dismiss the alert with a reason (or adjust the query), SonarQube — mark as "False Positive"
   with a comment.
7. **Report** a table: finding, location, verdict, severity, one-line reason, action. True positives first.

## Checklist

```text
- [ ] Findings grouped by rule and shared root cause (triage helpers once)
- [ ] For each: source, path (sanitization on every path?), sink, reachability
- [ ] Verdict: true positive / false positive (with reason) / needs info
- [ ] Severity re-rated by attacker access and impact
- [ ] True positives fixed at the root, with a test
- [ ] False positives suppressed in code with rule ID and reason
- [ ] Report table, true positives first
```

## Red Flags

- "It's validated somewhere upstream." (Where? On every path?)
- Suppressing a whole rule to silence noise.
- Marking 40 alerts false positive without opening the shared helper.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Scanners are always noisy." | Noise is a reason to triage carefully, not to skip — real bugs hide in noisy reports. |
| "The input comes from our own frontend." | Attackers don't use your frontend; any HTTP input is attacker-controlled. |
| "It's internal code." | Internal endpoints get reached via SSRF, compromised accounts, and misconfigured networks. |

## Anti-Patterns (What NOT to do)

* Do not mark a finding false positive without tracing the source, or because "the input is validated somewhere".
* Do not bulk-suppress a rule across the codebase to silence noise.
* Do not trust a sanitizer that only runs on some code paths.
* Do not keep the scanner's severity when reachability or impact clearly differ; explain the change.
* Do not write a working exploit; describe the attack in one sentence.

## Examples

### Example 1: four Bandit findings

**User:** "Bandit found 4 issues in our Flask app. Which ones are real?" *(bandit.json)*

**Expected output:**

```text
| # | Finding                         | Location              | Verdict        | Severity          | Reason |
|---|---------------------------------|-----------------------|----------------|-------------------|--------|
| 1 | B608 SQL built with f-string    | reports/views.py:48   | TRUE POSITIVE  | HIGH (was MEDIUM) | `sort` comes from request.args and is interpolated into ORDER BY; any logged-in user can inject |
| 2 | B602 subprocess shell=True      | tasks/thumbs.py:22    | TRUE POSITIVE  | HIGH              | uploaded filename reaches the shell string unescaped |
| 3 | B105 hard-coded password        | tests/conftest.py:9   | FALSE POSITIVE | —                 | test fixture password for the local test DB, not used in production |
| 4 | B311 random for token           | utils/ids.py:5        | NEEDS INFO     | —                 | random.choice builds `ref_code`; harmless if only a display reference, a bug if it is ever a secret |

## Fixes
1. reports/views.py:48 — map `sort` through an allow-list:
   SORTS = {"date": "created_at", "amount": "amount_cents"}; order = SORTS.get(sort, "created_at")
   and keep values parameterized. Test: ?sort=date;DROP returns 400 or the default order.
2. tasks/thumbs.py:22 — subprocess.run(["convert", src_path, "-resize", "200x200", dst_path], check=True)
   with no shell; paths built from a generated ID, not the uploaded filename.
3. tests/conftest.py:9 — `password = "test-only"  # nosec B105 - local test DB fixture`
4. Question: is ref_code ever used to authorize anything (e.g. guest access links)? If yes, use secrets.token_urlsafe().
```

### Example 2: a shared helper behind many alerts

**User:** "CodeQL reported 41 'path injection' alerts, all through our safe_join(base, user_path) helper."

**Expected output:**

```text
Triaged the helper once (utils/files.py:14):

def safe_join(base, user_path):
    return os.path.join(base, user_path)

Verdict: TRUE POSITIVE for all 41 — os.path.join doesn't prevent "../../etc/passwd", and an
absolute user_path replaces base entirely.

Fix (one place):
def safe_join(base, user_path):
    base = os.path.realpath(base)
    target = os.path.realpath(os.path.join(base, user_path))
    if os.path.commonpath([base, target]) != base:
        raise ValueError("path escapes base directory")
    return target

Tests: "../x", "/etc/passwd", "a/../../x", and a symlink pointing outside base → ValueError;
"reports/q3.pdf" → allowed. After the fix, CodeQL recognizes the containment check on re-scan
(if not, add a model or dismiss the alerts as "fixed in helper" with a link to the test).
```

## Quick Reference

| Question | Decides |
|---|---|
| Is the source attacker-controlled? | No → likely false positive |
| Sanitized on *every* path to the sink? | No → true positive |
| Reachable in production? | No → lower severity, still note it |
| Unauthenticated access? | Raises severity |
| Many alerts, one helper | Triage and fix the helper once |
| False positive | Suppress inline with rule ID + reason |
