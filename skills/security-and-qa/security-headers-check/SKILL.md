---
name: security-headers-check
description: Grades a website's HTTP security headers and cookies (CSP, HSTS, framing, CORS, cookie flags) and writes the server config to fix them. Use when hardening, launching, or pen-test prepping any web app.
compatibility: Bundled script requires Python 3.8+ (standard library only). Live mode needs network access to the target.
---

# Detailed Instructions

Measure the headers the site actually sends, then fix them where they are set (server, CDN, or
framework). A Content-Security-Policy that breaks the site gets removed the next day, so roll out
strict policies in report-only mode first.

## Overview

Security headers are cheap defense in depth: HSTS stops downgrade attacks, CSP limits the damage of
an XSS bug, frame protection stops clickjacking, and cookie flags keep session tokens away from
scripts and other sites. This skill runs `scripts/check_headers.py` against the site (or saved
headers), ranks the findings, and produces copy-paste config for the user's stack.

## Workflow Rules

1. **Scope:** only check sites the user owns or is authorized to test. The script sends ordinary
   GET requests — no payloads or probing.
2. **Collect headers:**
   - Live: `python3 scripts/check_headers.py https://app.example.com`
   - Offline or internal: `curl -sI https://app.example.com > headers.txt`, then
     `python3 scripts/check_headers.py https://app.example.com --headers-file headers.txt`
   Check the main HTML page and, separately, an authenticated page and an API response if they are
   served differently.
3. **Rank** the findings: HIGH (missing HSTS or CSP, unsafe script-src, CORS with credentials on
   `*`, no HTTPS redirect) before MEDIUM and LOW.
4. **Find where headers are set:** CDN (Cloudflare, CloudFront), reverse proxy (nginx, Caddy),
   platform config (`vercel.json`, `netlify.toml`), or app middleware (`helmet` for Express,
   `django.middleware.security` + `django-csp`, `secure_headers` for Rails). Fix at one layer to
   avoid duplicate or conflicting headers.
5. **CSP rollout:** start from an inventory of script, style, image, and connect sources; ship as
   `Content-Security-Policy-Report-Only` with a `report-to`/`report-uri` endpoint; fix violations;
   then enforce. Prefer nonces or hashes over `'unsafe-inline'`.
6. **HSTS rollout:** start with a short `max-age` if subdomains might still serve HTTP, then raise
   to at least one year. Add `preload` only when every subdomain is HTTPS-only — it is hard to undo.
7. **Cookies:** session and auth cookies need `Secure`, `HttpOnly`, and `SameSite=Lax` (or
   `Strict`); `HttpOnly` is optional only for cookies that JavaScript must read.
8. **Re-run the script** after the change and show the before/after summary.

## Anti-Patterns (What NOT to do)

* Do not enforce a strict CSP without a report-only phase; it will break real pages.
* Do not add `'unsafe-inline'` and `'unsafe-eval'` to make CSP errors go away; that removes most of its value.
* Do not set `preload` on HSTS without confirming every subdomain supports HTTPS.
* Do not set the same header in both the CDN and the app with different values.
* Do not treat a perfect header score as "secure"; headers mitigate bugs, they do not fix them.
* Do not run the check against sites the user is not authorized to test.

## Examples

**User:** "We launch Monday. Can you check our headers? Site is Express behind nginx."

**Expected output:**

```text
$ python3 scripts/check_headers.py https://shop.example
Checked: https://shop.example
  HIGH   Content-Security-Policy      script-src allows 'unsafe-inline' without nonces/hashes
  HIGH   CORS                         Allow-Origin * with Allow-Credentials true (misconfigured; check origin handling)
  MEDIUM Strict-Transport-Security    max-age=86400; use at least 31536000 (1 year)
  MEDIUM Framing                      no CSP frame-ancestors or X-Frame-Options; page can be framed (clickjacking)
  MEDIUM X-Content-Type-Options       should be 'nosniff'
  MEDIUM Set-Cookie session           missing Secure, HttpOnly, SameSite
  LOW    X-Powered-By                 reveals software: 'Express'
3 high, 5 medium, 7 low   (trimmed)

## Fix in the app (helmet), one layer only
app.disable("x-powered-by");
app.use(helmet({
  contentSecurityPolicy: {
    reportOnly: true,   // flip to false after a week with no unexpected reports
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", (req, res) => `'nonce-${res.locals.cspNonce}'`],
      objectSrc: ["'none'"], baseUri: ["'none'"], frameAncestors: ["'none'"],
      reportUri: ["/csp-report"],
    },
  },
  strictTransportSecurity: { maxAge: 31536000, includeSubDomains: true },
  referrerPolicy: { policy: "strict-origin-when-cross-origin" },
}));
app.use(session({ cookie: { secure: true, httpOnly: true, sameSite: "lax" } }));

CORS: replace `origin: "*"` with an allow-list (["https://shop.example"]) — credentials require it.

## Before Monday
Ship HSTS, nosniff, framing, cookie flags, and CORS now. Run CSP in report-only through launch
week, then enforce. Re-run the check after deploy.
```
