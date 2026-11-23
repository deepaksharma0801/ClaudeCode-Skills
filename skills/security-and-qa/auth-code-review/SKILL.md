---
name: auth-code-review
description: Reviews authentication and authorization code for broken access control, session and token flaws, and password storage. Use when reviewing login, sessions, API keys, roles, or permission checks.
---

# Detailed Instructions

Authentication asks "who are you?"; authorization asks "may you do this to *this* object?". Check
both on every path, and verify each finding by reading the code, not by pattern-matching names.
Broken access control is the most common serious web vulnerability, and it rarely looks like a bug:
an endpoint that checks the user is logged in but never checks that they own the record.

## When to Use

- Reviewing login, signup, password reset, sessions, JWT/OAuth handling, API keys
- Any endpoint that reads or changes an object by ID
- Role/permission systems, multi-tenant data access, admin features
- Pre-launch security review of an API

**Don't use when:** the task is designing a new feature's risks before code exists (use
`threat-model-lite`), or triaging scanner output (use `security-finding-triage`).

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

## Checklist

```text
- [ ] Every route mapped: how it authenticates, where it authorizes
- [ ] Object-level checks on every read/update/delete by ID (no IDOR)
- [ ] Function-level checks server-side for admin/internal routes
- [ ] No mass assignment of role/owner/tenant fields
- [ ] Tenant scoping in every multi-tenant query
- [ ] Password hashing (bcrypt/scrypt/Argon2), rate limits, no account enumeration
- [ ] Reset/invite tokens random, single-use, short-lived, stored hashed
- [ ] Cookies HttpOnly/Secure/SameSite; session rotation; CSRF where cookie-authenticated
- [ ] JWT algorithm pinned, signature and exp verified
- [ ] Findings with file:line, attack in one line, fix; passed checks listed
```

## Red Flags

- `findById(req.params.id)` with no owner or tenant condition.
- `User.update(req.body)`.
- Role checks only in the frontend.
- `jwt.decode` (not `verify`), or `algorithms` not pinned.
- "Only logged-in users can call this."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "IDs are UUIDs, nobody can guess them." | IDs leak through URLs, logs, emails, and shared links. Authorization must not depend on secrecy of IDs. |
| "The UI hides the admin button." | Attackers call the API directly. Enforce on the server. |
| "Our framework handles auth." | It handles authentication; object-level authorization is your code. |

## Anti-Patterns (What NOT to do)

* Do not accept "the route requires login" as proof of authorization.
* Do not report a finding without a file and line, or without reading the code path.
* Do not recommend rolling your own crypto or session scheme; point to the framework's built-in.
* Do not write working exploit code; describe the attack in one sentence.
* Do not bury critical access-control issues under style or hardening notes.

## Examples

### Example 1: an invoices API

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

### Example 2: a JWT verification bug

**User:** "Can you check our JWT middleware?"

```js
const payload = jwt.decode(token);
if (payload && payload.exp > Date.now()) req.user = payload;
```

**Expected output:**

```text
CRITICAL — middleware/auth.js:4 — signature never verified
jwt.decode only base64-decodes; anyone can craft {"sub":"admin"} and be accepted.
Also: exp is in seconds but Date.now() is in milliseconds, so every genuine token fails this check,
while a forged token with an enormous exp passes it.

Fix:
const payload = jwt.verify(token, process.env.JWT_PUBLIC_KEY, {
  algorithms: ["RS256"],          // pin the algorithm
  issuer: "https://auth.example.com",
  audience: "api",
});                                 // verify() checks signature and exp (in seconds)
req.user = { id: payload.sub, role: payload.role };

Add a test with an unsigned token and one signed by a different key; both must get 401.
```

## Quick Reference

| Area | Must be true |
|---|---|
| Object access | Query includes owner/tenant condition |
| Admin routes | Role checked on the server |
| Request bodies | Allow-listed fields only |
| Passwords | bcrypt/scrypt/Argon2; rate-limited login |
| Tokens (reset/invite) | ≥128-bit random, single-use, expiring, hashed at rest |
| Sessions | HttpOnly, Secure, SameSite; rotate on login; invalidate on logout |
| JWT | `verify` with pinned algorithm, issuer, audience |
