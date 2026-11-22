---
name: threat-model-lite
description: Produces a one-page STRIDE threat model with ranked risks and concrete mitigations. Use when designing or reviewing a feature that handles auth, user data, payments, or uploads.
---

# Detailed Instructions

Model the specific feature in front of you, not security in general. Every threat must name the
component it hits and a mitigation a developer can implement this sprint.

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

## Anti-Patterns (What NOT to do)

* Do not produce a generic OWASP checklist unrelated to the feature's actual flows.
* Do not list a threat without a mitigation, or a mitigation as vague as "validate input" or "use encryption".
* Do not rate everything High. If everything is critical, nothing is prioritized.
* Do not assume authentication implies authorization — check object-level access explicitly.
* Do not write exploit code; describe the attack scenario in one line.

## Examples

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
