---
name: api-design-review
description: Reviews a REST or HTTP API design for naming, status codes, errors, pagination, versioning, and breaking changes. Use for new endpoints, OpenAPI specs, or API pull requests.
---

# Detailed Instructions

An API is a contract you can't easily take back: once a client depends on a field name, a status
code, or an error shape, changing it breaks someone you may never hear from. Review for
**consistency with the rest of the API first**, then for convention, and classify every change to
an existing endpoint as breaking or not. A consistent API with a few unconventional choices beats a
"correct" endpoint that behaves differently from its neighbors.

## When to Use

- Designing new endpoints or a new API
- Reviewing an OpenAPI/Swagger spec, route definitions, or an API pull request
- Changing an existing endpoint's fields, status codes, or behavior
- Planning API versioning or deprecation

**Don't use when:** the API is GraphQL or gRPC (the principles carry over, but conventions differ —
say so and adapt), or the question is about authentication/authorization logic (use
`auth-code-review`).

## Overview

API problems are cheap to fix in review and expensive after clients ship: a verb in the URL, a
`200` with an error in the body, a list endpoint with no pagination that falls over at 50,000 rows,
money as a float, a renamed field. This skill first extracts the API's existing conventions, then
checks the design against a fixed list — resources, methods and status codes, errors, collections,
payloads, safety, and compatibility — and returns findings by severity with the corrected design.

## Workflow Rules

### 1. Learn the house style

1. **Collect existing conventions** from the spec or routes: field casing (`snake_case` vs
   `camelCase`), ID format, error shape, pagination style, date format, auth scheme, versioning
   approach, naming of filters and sort parameters. New endpoints should match them.
2. **If there is no existing API**, pick defaults once and write them down: snake_case JSON,
   RFC 9457 problem details for errors, cursor pagination, ISO 8601 UTC timestamps, `/v1` prefix.

### 2. Check the design

3. **Resources and URLs**
   - Plural nouns for collections (`/invoices`, `/invoices/{id}`); nest at most one level
     (`/customers/{id}/invoices`), otherwise use filters (`/invoices?customer_id=…`).
   - Verbs only for true actions that aren't CRUD: `POST /invoices/{id}/send`.
   - IDs in the path; filters, sorting, and pagination in the query.
4. **Methods and status codes**

   | Situation | Use |
   |---|---|
   | Read | `GET` (safe, cacheable) → `200` |
   | Create | `POST` → `201` + `Location` header + the created resource |
   | Async work accepted | `202` + a status URL |
   | Full replace / partial update | `PUT` (idempotent) / `PATCH` |
   | Delete | `DELETE` → `204` (idempotent: repeat delete → `204` or `404`, consistently) |
   | Malformed or invalid input | `400` / `422` (pick one and use it everywhere) |
   | Not authenticated / not allowed | `401` / `403` (or `404` to hide existence) |
   | Missing | `404` |
   | Conflict (duplicate, version mismatch) | `409` (or `412` with `If-Match`) |
   | Rate limited | `429` + `Retry-After` |

   Never return `200` with an error in the body — clients, proxies, and monitoring all read the status.
5. **Errors:** one shape everywhere, with a stable machine-readable `code`, a human `message`, and
   field-level details for validation. Don't leak stack traces or SQL.
6. **Collections:** paginated from day one, with a default and maximum page size; a stable sort
   order (add a unique tiebreaker like `id`); consistent filter names. Prefer cursor pagination for
   large or frequently changing data — offset pages skip and duplicate rows as data changes.
7. **Payloads**
   - Consistent casing; no internal fields (`password_hash`, `internal_notes`, raw DB IDs if you
     use public IDs).
   - Timestamps in ISO 8601 with timezone (`2026-11-23T14:05:00Z`).
   - Money as integer minor units plus currency (`amount_cents: 1250, currency: "USD"`), never floats.
   - Enums as lowercase strings, documented; clients must tolerate new values.
   - Decide `null` vs missing and be consistent.
8. **Safety and limits:** idempotency keys (`Idempotency-Key` header) on `POST` that create
   payments, orders, or messages; documented rate limits; authorization stated per endpoint;
   request size limits.

### 3. Classify compatibility

9. **For every change to an existing endpoint**, classify it:

   | Breaking | Non-breaking |
   |---|---|
   | Removing or renaming a field, endpoint, or enum value | Adding an optional request field |
   | Changing a field's type or format | Adding a response field |
   | Making an optional input required | Adding an endpoint |
   | Changing a status code or error code | Adding an enum value (if clients were told to tolerate unknowns) |
   | Changing default sort, page size, or behavior | Relaxing validation |

   Breaking changes need a new version or an additive alternative plus a deprecation period
   (`Deprecation` and `Sunset` headers, changelog entry, usage monitoring before removal).

### 4. Report

10. **Findings by severity:** Must fix (incorrect or breaking), Should fix (inconsistent with house
    style or convention), Consider (improvements). Each finding shows the corrected design, not
    just the complaint.

## Checklist

```text
- [ ] Existing conventions extracted (casing, errors, pagination, dates, IDs, versioning)
- [ ] URLs: plural nouns, ≤ 1 level nesting, verbs only for actions
- [ ] Methods and status codes correct; no 200-with-error
- [ ] One error shape with stable codes
- [ ] Every list endpoint paginated with a max page size and stable sort
- [ ] Payloads: casing, ISO 8601 UTC, money in minor units, string enums, no internal fields
- [ ] Idempotency keys for create-payment/order endpoints; rate limits documented
- [ ] Every change to an existing endpoint classified breaking / non-breaking
- [ ] Findings grouped Must / Should / Consider with corrected designs
```

## Red Flags

- Reviewing a new endpoint without reading two existing ones first.
- "It's just renaming a field." (Renames are breaking for every client.)
- 200 OK with `{"error": ...}` in the body.
- Offset pagination on a table that grows by millions of rows.
- Calling a change "non-breaking" without checking enum additions, required fields, and defaults.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Only our frontend uses it." | Mobile apps on old versions, scripts, and partners call it too, often unseen. |
| "We'll version it later." | Without a versioning plan, the first breaking change becomes an outage. |
| "REST purity doesn't matter." | It doesn't. Consistency with the rest of *this* API does. |
| "Clients should ignore unknown fields." | Many don't; strict deserializers break on additions to enums. |

## Anti-Patterns (What NOT to do)

* **Imposing a new convention on one endpoint** — clients now need two code paths; match the API.
* **Approving an unpaginated list "because the data is small today"** — adding pagination later is a breaking change.
* **Calling a change non-breaking without checking every field and status code** — clients depend on details you didn't think of.
* **Floats for money** — rounding errors become accounting discrepancies.
* **Debating REST purity on a design that's consistent and clear** — spend review time on what will break.
* **Inventing the existing conventions** — read them from the spec or code.

## Examples

### Example 1: new endpoints

**User:** "Review these new endpoints before we publish them."

```text
POST /api/v1/createInvoice          → 200 { "success": false, "error": "bad amount" }
GET  /api/v1/invoices?customer=12   → 200 [ ...all invoices... ]
PUT  /api/v1/invoices/{id}          → body: { "Amount": 12.5, "status": "Paid" }
```

**Expected output:**

```text
House style (from openapi.yaml): snake_case, plural resources, cursor pagination
({ data, next_cursor }), errors { error: { code, message, fields } }, amounts in cents.

## Must fix
1. POST /createInvoice → POST /api/v1/invoices, returning 201 + Location: /api/v1/invoices/{id}.
2. Errors returned with 200. Use 422 and the standard shape:
   { "error": { "code": "invalid_amount", "message": "Amount must be positive",
                "fields": { "amount_cents": "must be > 0" } } }
3. GET /invoices returns every row. Add ?limit (default 50, max 200) and ?cursor, sorted by
   created_at desc, id desc; return { "data": [...], "next_cursor": "..." } like /customers.
4. "Amount": 12.5 → "amount_cents": 1250, "currency": "USD". Floats lose cents.

## Should fix
5. Casing: "Amount", "status": "Paid" → snake_case field names, lowercase enum values ("paid").
6. ?customer=12 → ?customer_id=12, matching /payments.
7. If clients send partial updates, use PATCH; PUT replaces the whole invoice.

## Consider
8. Accept an Idempotency-Key header on POST /invoices so retries can't create duplicates.
```

### Example 2: a change to a live endpoint

**User:** "We want to rename `total` to `total_cents` in GET /orders/{id} and make `currency` required on POST /orders. Any issue?"

**Expected output:**

```text
Both are breaking changes for existing clients:
- Renaming a response field: clients reading `total` get undefined.
- Making an optional input required: existing POSTs without `currency` start failing with 422.

Non-breaking path:
1. Add `total_cents` alongside `total` (both returned). Mark `total` deprecated in the spec and
   changelog; send `Deprecation: true` and `Sunset: <date>` headers on responses that include it.
2. Default `currency` to the account's currency when omitted; log requests that omit it.
3. Watch usage (field access logs or client versions) and remove `total` / require `currency`
   in /v2, or in /v1 after the sunset date once usage is near zero.
```

## Quick Reference

| Topic | Default |
|---|---|
| Collection URL | `/resources`, `/resources/{id}`, one nesting level max |
| Create | `POST` → `201` + `Location` |
| Errors | One shape, stable `code`, field details; never `200` |
| Lists | Cursor pagination, default + max page size, stable sort |
| Time | ISO 8601 with `Z` |
| Money | Integer minor units + currency |
| Retries on create | `Idempotency-Key` header |
| Changing a live field | Add new, deprecate old, remove later |
