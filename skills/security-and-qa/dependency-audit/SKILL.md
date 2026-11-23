---
name: dependency-audit
description: Audits a project's dependencies for known vulnerabilities, stale or unpinned versions, and risky licenses. Use when asked to audit, upgrade, or assess the security of a project's dependencies.
---

# Detailed Instructions

Run the ecosystem's own audit tool, then triage. Report what is exploitable and fixable first;
do not dump raw scanner output on the user.
Raw scanner output is long, mostly dev-only, and often fixed by a minor bump; if it isn't triaged,
teams either panic or ignore all of it — including the one exploitable runtime issue.

## When to Use

- "Audit our dependencies", "are we vulnerable?", pre-launch or compliance checks
- A Dependabot/Snyk/`npm audit` report that needs prioritizing
- A newly disclosed CVE in a popular package ("are we affected by …?")
- Inheriting a codebase with an old lockfile

**Don't use when:** the task is upgrading one framework across major versions (use
`dependency-upgrade-planner`), or reviewing first-party code findings from SAST tools (use
`security-finding-triage`).

## Overview

Scanners produce long lists where most entries are dev-only, unreachable, or already fixed by a
minor bump. This skill detects the package manager, runs the right audit, and turns the output
into a prioritized table with a concrete upgrade path for each issue.

## Workflow Rules

1. Detect ecosystems from lockfiles and manifests:

   | File | Audit command |
   |---|---|
   | `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` | `npm audit --json` / `pnpm audit --json` / `yarn npm audit --json` |
   | `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock` | `pip-audit -f json` (or `uvx pip-audit`) |
   | `Cargo.lock` | `cargo audit --json` |
   | `go.mod` | `govulncheck ./...` |
   | `Gemfile.lock` | `bundle audit check` |

   If the tool is not installed, say which one is missing and how to install it; do not invent
   results.
2. For each vulnerability record: package, installed version, fixed version, severity, advisory ID,
   and whether it is a **direct** or **transitive** dependency, and **runtime** or **dev-only**.
3. Prioritize: runtime + high/critical + fix available first; dev-only and no-fix-available last.
4. For each fix, give the exact command (e.g. `npm install lodash@4.17.21`) and say whether it is
   a patch, minor, or **major** bump. Flag major bumps as needing a changelog review.
5. Check hygiene: missing lockfile, unpinned or wildcard ranges (`*`, `latest`, `>=` with no
   upper bound) in application code, and packages more than 2 major versions behind.
6. Check licenses of direct dependencies when the user asks or the project is commercial; flag
   AGPL/GPL/SSPL and "UNKNOWN".
7. Summarize with counts by severity and a short ordered action list.

## Checklist

```text
- [ ] Ecosystems detected from lockfiles; right audit tool run (or missing tool named)
- [ ] Each finding: package, installed → fixed version, severity, advisory ID
- [ ] Direct vs transitive; runtime vs dev-only
- [ ] Reachability considered for high/critical (is the vulnerable function used?)
- [ ] Exact upgrade command per fix; major bumps flagged
- [ ] Hygiene: lockfile present, no wildcard ranges, very stale packages
- [ ] Licenses checked when relevant
- [ ] Summary counts and an ordered action list
```

## Red Flags

- "Run `npm audit fix --force`."
- "237 vulnerabilities — we're compromised."
- "It's only transitive, so it doesn't matter."
- Reporting a CVE without the installed and fixed versions.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Auto-fix everything." | `--force` applies breaking majors silently. Review majors; take patches and minors freely. |
| "Dev dependencies can't hurt us." | Mostly true for runtime, but build tools run in CI with secrets. Low priority, not zero. |
| "Transitive issues aren't ours." | They ship in your bundle. Use overrides/resolutions when the parent won't update. |

## Anti-Patterns (What NOT to do)

* Do not run `npm audit fix --force` or any auto-upgrade without the user's go-ahead; it can apply
  breaking major versions.
* Do not report a CVE without the installed version and the fixed version.
* Do not treat every finding as urgent. A dev-only, unreachable issue is not a production incident.
* Do not recommend removing or replacing a package without checking what in the code uses it.
* Do not invent advisory IDs, severities, or fixed versions. If the scanner did not say, write
  "unknown".

## Examples

### Example 1: a pre-launch Node audit

**User:** "Can you audit the deps on this Node app before we launch?"

**Expected output:**

```text
Ecosystem: npm (package-lock.json) · Ran: npm audit --json
Found 7 advisories: 1 critical, 2 high, 3 moderate, 1 low

## Fix now (runtime, fix available)
| Package   | Installed | Fixed   | Sev      | Path                 | Command                         |
|-----------|-----------|---------|----------|----------------------|---------------------------------|
| jsonwebtoken | 8.5.1  | 9.0.0   | critical | direct               | npm i jsonwebtoken@9 (MAJOR — review verify() options) |
| axios     | 1.6.0     | 1.7.4   | high     | direct               | npm i axios@1.7.4 (minor)       |

## Fix soon
| semver | 6.3.0 | 6.3.1 | moderate | transitive via @babel/core (dev-only) | npm update semver |

## Low priority / no fix
- 3 moderate + 1 low, all dev-only via the test toolchain.

## Hygiene
- `"express": "*"` in package.json — pin to ^4.21.0.

## Next steps
1. Upgrade axios (safe minor).
2. Upgrade jsonwebtoken to 9 and rerun auth tests.
3. Pin express. Rerun `npm audit` to confirm 0 runtime highs.
```

### Example 2: "are we affected by this CVE?"

**User:** "There's a new security advisory for `requests` — are we affected?" *(Python service)*

**Expected output:**

```text
$ pip-audit -f json   (uvx pip-audit)
requests 2.31.0 → fixed in 2.32.0 (GHSA-9wx4-h78v-vm56, CVSS 5.6 — "Session verify=False persists")

Installed via: direct dependency (requirements.txt pins requests==2.31.0).
Reachability: the advisory affects code that makes a request with verify=False and later requests
to the same host on the same Session. grep shows one Session with verify=False in
scripts/legacy_sync.py (internal tool, not the service). The service never disables verification.

Verdict: affected package, low practical exposure. Upgrade anyway (patch-level, low risk):
  change the pin in requirements.txt to requests==2.32.3, then pip install -r requirements.txt
and remove verify=False from scripts/legacy_sync.py.
```

## Quick Reference

| Ecosystem | Command |
|---|---|
| npm / pnpm / yarn | `npm audit --json` / `pnpm audit --json` / `yarn npm audit --json` |
| Python | `pip-audit -f json` (or `uvx pip-audit`) |
| Rust | `cargo audit --json` |
| Go | `govulncheck ./...` (reports reachable vulns) |
| Ruby | `bundle audit check --update` |
| Priority | runtime + high/critical + fix available → first |
| Transitive stuck | npm `overrides`, yarn `resolutions`, pip constraints |
