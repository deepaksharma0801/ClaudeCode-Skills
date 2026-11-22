---
name: auth-code-review
description: Reviews authentication and authorization code for broken access control, session and token flaws, and password storage. Use when reviewing login, sessions, API keys, roles, or permission checks.
---

# Detailed Instructions

Authentication asks "who are you?"; authorization asks "may you do this to *this* object?". Check
both on every path, and verify each finding by reading the code, not by pattern-matching names.

## Overview

Broken access control is the most common serious web vulnerability, and it rarely looks like a bug:
an endpoint that checks the user is logged in but not that they own the record. This skill walks a
focused checklist over auth code and reports concrete, located findings with fixes.

## Workflow Rules

1. **Map the surface:** list routes or handlers, how each authenticates (session, JWT, API key,
   none), and where authorization is enforced (middleware, decorator, inline check).
2. **Authorization (check first):**
   - Object-level: every read/update/delete by ID verifies ownership or tenant (`WHERE id = ? AND
     org_id = ?`), not just login. Look for IDOR.
   - Function-level: admin and internal routes require the role server-side; hidden UI is not a control.
   - Mass assignment: request bodies cannot set `role`, `is_admin`, `org_id`, `owner_id`.
   - Multi-tenant queries always scope by tenant.
3. **Authentication:**
   - Passwords hashed with bcrypt, scrypt, or Argon2 — never plain SHA/MD5; no plaintext logging.
   - Login and reset rate-limited; error messages do not reveal whether an account exists.
   - Reset and invite tokens are random (>= 128 bits), single-use, short-lived, and stored hashed.
4. **Sessions and tokens:**
   - Cookies `HttpOnly`, `Secure`, `SameSite`; session ID rotated on login; invalidated on logout
     and password change.
   - JWT: algorithm pinned (no `none`, no HS/RS confusion), signature and `exp` verified, secrets not
     hard-coded; revocation strategy exists for long-lived tokens.
   - CSRF protection on cookie-authenticated state-changing requests.
5. **Secrets:** API keys compared in constant time, stored hashed, scoped, and rotatable.
6. **Report** each finding: severity, `file:line`, what an attacker can do (one line), and the fix.
   Note checks that passed, so the reviewer knows what was covered.

## Anti-Patterns (What NOT to do)

* Do not accept "the route requires login" as proof of authorization.
* Do not report a finding without a file and line, or without reading the code path.
* Do not recommend rolling your own crypto or session scheme; point to the framework's built-in.
* Do not write working exploit code; describe the attack in one sentence.
* Do not bury critical access-control issues under style or hardening notes.

## Examples

**User:** "Review the auth on our invoices API before launch."

**Expected output:**

```text
## Surface
| Route                      | AuthN   | AuthZ enforced               |
|----------------------------|---------|------------------------------|
| GET  /api/invoices         | session | scoped by org (ok)           |
| GET  /api/invoices/:id     | session | none — loads by id only      |
| PATCH /api/invoices/:id    | session | owner check (ok)             |
| POST /api/users/:id        | session | none                         |
| POST /api/password-reset   | none    | n/a                          |

## Findings
1. CRITICAL — IDOR — routes/invoices.ts:41
   Any logged-in user can read any organization's invoice by changing :id.
   Fix: Invoice.findOne({ id, orgId: req.user.orgId }); add a test with a second org.

2. HIGH — Mass assignment — routes/users.ts:63
   `User.update(req.body)` lets a user set `role: "admin"` on themselves.
   Fix: allow-list fields (name, avatarUrl); never accept role from the client.

3. MEDIUM — Reset token — services/reset.ts:18
   Token is Math.random().toString(36) and never expires.
   Fix: crypto.randomBytes(32), store a hash, expire after 30 minutes, single use.

4. LOW — Account enumeration — routes/auth.ts:30
   "No account with that email" vs "Wrong password". Use one generic message.

## Passed
- bcrypt (cost 12) for passwords; session cookie HttpOnly + Secure + SameSite=Lax; session rotated on login.
```
