---
name: threat-model-lite
description: Produces a one-page STRIDE threat model with ranked risks and concrete mitigations. Use when designing or reviewing a feature that handles auth, user data, payments, or uploads.
---

# Detailed Instructions

Model the specific feature in front of you, not security in general. Every threat must name the
component it hits and a mitigation a developer can implement this sprint.
Full threat-modeling workshops rarely happen for everyday features, so the obvious risks ship.
A one-page model done while the design is still cheap to change catches most of them.

## When to Use

- Designing or reviewing a feature that touches auth, user data, payments, uploads, sharing,
  webhooks, admin tools, or third-party integrations
- Security review before launch
- "What could go wrong with this design?"

**Don't use when:** reviewing existing auth code line by line (use `auth-code-review`), or
triaging scanner findings (use `security-finding-triage`).

## Overview

Full threat-modeling workshops rarely happen for everyday features, so obvious risks ship. This
skill does a fast, structured pass: draw the data flow, mark trust boundaries, walk STRIDE at each
boundary, and rank what matters by likelihood and impact.

## Workflow Rules

1. **Scope** in one sentence: the feature, who uses it, what data it touches.
2. **Data flow:** list actors, components, data stores, and the flows between them. Mark each
   **trust boundary** (browser → API, API → third party, service → database, user upload → storage).
   Render it as a short text or Mermaid diagram.
3. **Assets:** what an attacker would want (accounts, PII, money, admin access, availability).
4. **STRIDE at each boundary** — consider all six, report only real ones:
   Spoofing (auth), Tampering (integrity), Repudiation (audit logs), Information disclosure,
   Denial of service, Elevation of privilege (authorization, IDOR).
5. For each threat: ID, boundary, a one-line attack scenario, likelihood (L/M/H), impact (L/M/H),
   and a concrete mitigation (library, check, config) — plus whether it already exists in the code.
6. **Rank** by likelihood × impact and put the top 3 in an "Do before launch" list.
7. If code is available, verify claimed mitigations exist (e.g. find the authorization check)
   instead of assuming.
8. List **open questions** you could not answer from the material provided.

## Checklist

```text
- [ ] Scope in one sentence: feature, users, data
- [ ] Data flow with trust boundaries marked
- [ ] Assets listed
- [ ] STRIDE walked at each boundary; only real threats kept
- [ ] Each threat: scenario, likelihood, impact, concrete mitigation, exists in code?
- [ ] Claimed mitigations verified in code where available
- [ ] Top 3 "do before launch"
- [ ] Open questions listed
```

## Red Flags

- A threat list that would fit any feature ("SQL injection, XSS, CSRF…") with no data flow.
- Everything rated High.
- "Users must be logged in, so it's fine."
- Mitigations like "validate input" or "use encryption".

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "We use a framework, so it's secure." | Frameworks cover common bugs, not your authorization rules or business logic. |
| "Only logged-in users can reach it." | Authentication isn't authorization; any logged-in user may be the attacker. |
| "It's internal." | Internal tools get phished accounts and over-broad access; model them too. |

## Anti-Patterns (What NOT to do)

* Do not produce a generic OWASP checklist unrelated to the feature's actual flows.
* Do not list a threat without a mitigation, or a mitigation as vague as "validate input" or "use encryption".
* Do not rate everything High. If everything is critical, nothing is prioritized.
* Do not assume authentication implies authorization — check object-level access explicitly.
* Do not write exploit code; describe the attack scenario in one line.

## Examples

### Example 1: share invoice by link

**User:** "We're adding 'share invoice by link' — anyone with the link can view a PDF of the invoice."

**Expected output:**

```text
## Scope
Invoice owners create a public link; anyone with the link can view the invoice PDF. Data: customer
name, address, line items, amounts.

## Data flow
Owner (browser) → API: POST /invoices/{id}/share → DB (share_tokens)
Anyone (browser) → API: GET /s/{token} → DB → PDF renderer → object storage
Trust boundaries: browser→API (both flows), API→object storage

## Threats
| ID | Boundary            | Threat (STRIDE)        | Scenario                                         | L | I | Mitigation | Exists? |
|----|---------------------|------------------------|--------------------------------------------------|---|---|------------|---------|
| T1 | browser→API (GET)   | Info disclosure        | Tokens are sequential IDs; attacker enumerates /s/1..N | H | H | 128-bit random token (secrets.token_urlsafe(32)) | No — uses invoice ID |
| T2 | browser→API (POST)  | Elevation of privilege | User shares someone else's invoice by changing {id} | M | H | Check invoice.owner_id == current_user before creating token | Yes (invoices.py:88) |
| T3 | API→storage         | Info disclosure        | PDF served from public bucket URL that never expires | M | H | Private bucket + signed URL, 5-min expiry | No |
| T4 | browser→API (GET)   | Info disclosure        | Link forwarded or indexed; no way to revoke      | M | M | Expiry (30 days default) + revoke button | No |
| T5 | browser→API (GET)   | Denial of service      | Token endpoint hammered, PDF rendered each time  | L | M | Cache rendered PDF; rate-limit per IP | Partial |
| T6 | all                 | Repudiation            | No record of who viewed a shared invoice         | L | L | Log token, IP, timestamp per view | No |

## Do before launch
1. T1 — replace invoice-ID links with random tokens.
2. T3 — serve PDFs via signed, expiring URLs.
3. T4 — add link expiry and revocation.

## Open questions
- Should links require the viewer's email (stronger), or stay bearer links?
```

### Example 2: a webhook receiver

**User:** "We're adding an endpoint that receives payment webhooks from our provider and marks orders paid."

**Expected output:**

```text
## Data flow
Provider → (internet) → POST /webhooks/payments → verify → update orders → enqueue receipt email
Trust boundary: internet → our API (anyone can call this URL)

## Threats
| ID | Threat (STRIDE) | Scenario | L | I | Mitigation |
|----|-----------------|----------|---|---|------------|
| T1 | Spoofing | Attacker posts a fake "paid" event and gets goods free | H | H | Verify the provider's signature header with the webhook secret; reject if invalid |
| T2 | Tampering / replay | Valid old event replayed to re-trigger fulfillment | M | M | Reject timestamps older than 5 min; store processed event IDs (idempotency) |
| T3 | Info disclosure | Error responses echo payloads with customer data | L | M | Return 400/200 with no body detail; log event ID only |
| T4 | DoS | Flood of junk requests | M | L | Verify signature before any DB work; rate-limit by IP |
| T5 | Elevation | Event for order A marks order B paid (ID from payload trusted blindly) | M | H | Look up the payment by provider ID and match amount + currency + order before updating |

## Do before launch
1. T1 signature verification  2. T5 amount/order matching  3. T2 idempotency on event ID
```

## Quick Reference

| Boundary | Ask |
|---|---|
| Browser → API | Who is the caller, and may they touch *this* object? |
| Internet → webhook | Is the sender verified (signature), and is it a replay? |
| API → third party | What do we send, and what if the response is malicious? |
| User upload → storage | Type/size limits, malware, public access, served from where? |
| Service → DB | Least privilege; tenant scoping in every query |
| Ranking | Likelihood × impact; top 3 before launch |
