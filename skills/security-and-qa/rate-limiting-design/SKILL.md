---
name: rate-limiting-design
description: Designs or reviews API rate limits with the right key, algorithm, traffic-based limits, 429 responses, and abuse protection for login and costly endpoints. Use when adding rate limits.
---

# Detailed Instructions

Pick limits from real traffic, not round numbers: measure what normal clients do, set the limit
comfortably above that, and set tighter limits on endpoints that are expensive or attractive to
attackers (login, password reset, signup, search, AI generation, SMS). Key the limit by the
identity you actually trust (API key or user, not just IP), share the counters across instances,
and tell clients exactly when to retry.

## When to Use

- Adding rate limits to an API or a specific endpoint
- "We're getting brute-forced / scraped / hit by a runaway client"
- Protecting expensive operations (LLM calls, exports, SMS/email sends) from cost abuse
- Reviewing an existing limiter's design

**Don't use when:** the problem is volumetric DDoS at the network layer (that's CDN/WAF
territory), or legitimate load needs capacity planning (use `load-test-planner`).

## Overview

Limiters fail in a few ways: keyed by IP so whole offices get blocked while attackers rotate
IPs, kept in process memory so each of 10 instances allows 10× the limit, a fixed window that
lets 2× bursts at the boundary, no `Retry-After`, and no special protection on login. This
skill picks the key, algorithm, and limits per endpoint class, defines the response contract,
and covers abuse-specific controls.

## Workflow Rules

1. **Classify endpoints:** normal reads, writes, expensive (search, exports, LLM, reports),
   sensitive (login, password reset, OTP verify, signup), and outbound-cost (SMS, email).
2. **Choose the key:**
   - Authenticated API: API key or user/account id (per tenant for B2B).
   - Unauthenticated: IP (careful with NAT and IPv6 — limit by /64 for IPv6) plus, for login, the
     **target account** (stops distributed brute force on one user).
   - Behind a proxy/CDN: take the client IP only from trusted proxy headers, configured
     explicitly — `X-Forwarded-For` is client-controlled otherwise.
3. **Choose the algorithm:** token bucket (allows short bursts, smooth average) for APIs; sliding
   window for strict per-window caps. Avoid plain fixed windows (2× burst at the boundary).
4. **Set limits from data:** take p99 requests/min per key from logs for each class and set
   the limit at roughly 2–5× that for normal endpoints; sensitive endpoints get absolute small
   limits (e.g. 5 login failures per account per 15 min, then backoff or CAPTCHA).
5. **Shared state:** use Redis (atomic Lua script or `INCR` + `EXPIRE`) or the gateway's limiter,
   not per-process memory. Decide **fail-open or fail-closed** if the store is down: open for
   normal APIs, closed for login/OTP/SMS.
6. **Response contract:** `429 Too Many Requests` with `Retry-After` (seconds), and optionally
   `RateLimit-Limit`/`RateLimit-Remaining`/`RateLimit-Reset` headers; a stable error code in the
   body. Document limits for API consumers.
7. **Abuse-specific controls:** for OTP/verification codes, cap attempts per code and per account
   (a 6-digit code falls to brute force without it); for SMS, cap per phone number and per
   destination country (toll fraud); for signups, add bot detection.
8. **Observe:** count 429s by key and endpoint, alert on spikes, and allow per-customer overrides
   for legitimate heavy users.

## Checklist

```text
- [ ] Endpoints classified (normal, expensive, sensitive, outbound-cost)
- [ ] Key per class; trusted proxy config for client IP; IPv6 /64
- [ ] Login limited per account and per IP
- [ ] Token bucket or sliding window, not fixed window
- [ ] Limits derived from p99 traffic per key
- [ ] Shared store; fail-open/closed decided per class
- [ ] 429 + Retry-After (+ RateLimit headers); documented
- [ ] OTP attempts capped; SMS caps per number and country
- [ ] 429 metrics, alerts, and override process
```

## Red Flags

- An in-memory limiter on a horizontally scaled service.
- Trusting `X-Forwarded-For` from anyone.
- Login limited only by IP.
- `limit = 1000` chosen because it's round.
- 429 with no `Retry-After`, so clients retry immediately.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "IP limiting is enough." | Attackers rotate IPs cheaply; offices and mobile carriers share one IP. |
| "Our auth stops brute force." | Without per-account attempt limits, passwords and OTPs fall to guessing. |
| "We'll set generous limits, nobody will hit them." | Then they don't stop a runaway script or a cost attack. |
| "The CDN handles it." | CDNs don't know your users, tenants, or which endpoints are expensive. |

## Anti-Patterns (What NOT to do)

* **Same limit for every endpoint** — too loose for login, too tight for reads.
* **Fixed windows** — allow double bursts at the boundary.
* **Silent dropping or 500s instead of 429** — clients can't back off correctly.
* **Fail-closed for everything** — a Redis blip becomes a full outage.
* **No override path** — your biggest customer gets blocked during a legitimate import.

## Examples

### Example 1: a public API with login

**User:** "Design rate limits for our API. Logs show p99 per API key is 120 req/min; login gets
credential-stuffing attempts."

**Expected output:**

```markdown
| Class | Key | Algorithm | Limit | Store down |
|---|---|---|---|---|
| Reads | API key | Token bucket | 600/min, burst 100 | Fail open |
| Writes | API key | Token bucket | 300/min, burst 30 | Fail open |
| Exports / search | API key | Sliding window | 10/min | Fail open |
| Login | account (email) + IP | Sliding window | 5 failures / 15 min per account; 30 / 15 min per IP | Fail closed |
| Password reset | account + IP | Sliding window | 3 / hour per account | Fail closed |

Reads at 600/min (5× the 120/min p99) and writes at 300/min (2.5×, since writes cost more) leave
room for normal spikes. Revisit after a week of 429 data.

**Login:** after 5 failures, require a CAPTCHA or add exponential delay; notify the user on
lockout-level activity. Per-account limiting stops distributed stuffing against one user; per-IP
catches one source trying many accounts.

**Implementation:** Redis token bucket via an atomic Lua script, keyed `rl:{class}:{key}`.
Client IP from `X-Forwarded-For` only via the load balancer's trusted hop.

**Response:** `429` + `Retry-After: <seconds>` + `RateLimit-Remaining`; body
`{"error":{"code":"rate_limited"}}`. Limits published in the API docs; enterprise overrides via
config.
```

### Example 2: an SMS verification endpoint

**User:** "Our `/send-code` endpoint cost us $40k last month in SMS. It's limited to 10/min per IP."

**Expected output:**

```text
Likely SMS pumping (toll fraud): bots trigger codes to premium-rate numbers from rotating IPs,
so a per-IP limit doesn't help. Add:
1. Per phone number: 3 sends / hour, 10 / day.
2. Per destination country: block or tightly cap countries you don't serve; alert on spikes.
3. Per account/session: require a signed-in or CAPTCHA-verified session before sending.
4. Verify attempts: 5 tries per code, codes expire in 10 min.
5. Alert on daily SMS spend above baseline; most providers also offer fraud guard settings.
```

## Quick Reference

| Decision | Default |
|---|---|
| Key | API key / user; login = account + IP |
| Client IP | Trusted proxy header only; IPv6 /64 |
| Algorithm | Token bucket (APIs), sliding window (sensitive) |
| Limits | 2–5× p99 per key; small absolutes for sensitive |
| Store | Redis / gateway, shared |
| Failure | Open for normal, closed for sensitive |
| Response | 429 + Retry-After (+ RateLimit-*) |
| Abuse | OTP attempt caps; SMS per-number/country caps |
