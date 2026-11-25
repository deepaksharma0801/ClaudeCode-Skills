# Security & QA Skills

Skills for keeping secrets out of repos, finding risky dependencies, and testing what matters.

- **[secrets-precommit-check](secrets-precommit-check)** — Scan staged changes for keys, tokens, and `.env` files before they leave the machine.
- **[dependency-audit](dependency-audit)** — Run the right audit tool per ecosystem and triage findings into a prioritized fix list.
- **[threat-model-lite](threat-model-lite)** — One-page STRIDE threat model with ranked risks and concrete mitigations.
- **[test-plan-writer](test-plan-writer)** — Risk-based test plan for a change, then write the must-have tests.
- **[auth-code-review](auth-code-review)** — Review login, sessions, tokens, and permission checks for broken access control.
- **[accessibility-audit](accessibility-audit)** — Audit a page or component against WCAG 2.2 AA with located issues and code fixes.
- **[flaky-test-investigator](flaky-test-investigator)** — Reproduce an intermittent test failure, classify the cause, and make it deterministic.
- **[privacy-data-review](privacy-data-review)** — Trace personal data through a change and flag leaks, over-collection, and missing deletion.
- **[security-headers-check](security-headers-check)** — Grade security headers and cookies, then write the server config that fixes them.
- **[security-finding-triage](security-finding-triage)** — Trace scanner findings from source to sink to separate real bugs from false positives.
- **[iam-policy-review](iam-policy-review)** — Lint AWS IAM policies for wildcards and escalation paths, then rewrite them least-privilege.
- **[leaked-secret-response](leaked-secret-response)** — Respond to an exposed key: rotate first, check for abuse, then clean up and prevent.
- **[injection-review](injection-review)** — Trace untrusted input to SQL, shell, template, HTML, URL, and file sinks, and fix structurally.
- **[e2e-test-writer](e2e-test-writer)** — Write stable Playwright tests for critical flows with role locators and per-test data.
- **[file-upload-review](file-upload-review)** — Review uploads end to end: type by content, server-side names, private storage, safe serving.
- **[load-test-planner](load-test-planner)** — Plan k6 load tests from real traffic with SLO thresholds, then find the bottleneck.
