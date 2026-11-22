---
name: api-design-review
description: Reviews a REST or HTTP API design for naming, status codes, errors, pagination, versioning, and breaking changes. Use when designing new endpoints or reviewing an OpenAPI spec or API PR.
---

# Detailed Instructions

An API is a contract you cannot easily take back. Review for consistency with the rest of the API
first, then for convention, and flag every change that would break an existing client.

## Overview

API problems are cheap to fix in review and expensive after clients depend on them: a verb in a
URL, a `200` with an error body, a list endpoint with no pagination, a renamed field. This skill
checks a design (OpenAPI file, route code, or a description) against a fixed checklist and the
API's own existing conventions.

## Workflow Rules

1. **Collect the existing conventions** from the current API (spec or routes): casing
   (`snake_case` vs `camelCase`), ID format, error shape, pagination style, auth scheme, versioning.
   New endpoints should match them even if another style is "better".
2. **Resources and URLs:** plural nouns (`/invoices/{id}`), no verbs except for true actions
   (`POST /invoices/{id}/send`), nesting at most one level, IDs in the path not the query.
3. **Methods and status codes:** `GET` safe, `PUT`/`DELETE` idempotent, `POST` create → `201` +
   `Location`, async → `202`, validation → `400`/`422`, auth → `401` vs `403`, missing → `404`,
   conflict → `409`, rate limit → `429` with `Retry-After`. Never `200` with an error body.
4. **Errors:** one consistent shape (e.g. RFC 9457 `application/problem+json`) with a stable
   machine-readable `code`, a human message, and field-level details for validation.
5. **Collections:** paginated from day one (cursor preferred for large or changing data), a max
   page size, stable sort order, filter and sort parameters named consistently.
6. **Payloads:** consistent casing, ISO 8601 timestamps in UTC, money as integer minor units plus
   currency, enums as strings, no nulls-vs-missing ambiguity, no internal fields leaked.
7. **Safety:** idempotency keys for `POST` that create payments or orders; rate limits documented;
   authorization stated per endpoint.
8. **Breaking changes:** for any change to an existing endpoint, classify it. Removing or renaming
   a field, changing a type, making an optional input required, or changing a status code is
   breaking — require a new version or an additive alternative.
9. Report findings as Must fix / Should fix / Consider, each with the corrected design.

## Anti-Patterns (What NOT to do)

* Do not push a new convention onto one endpoint when the rest of the API uses another.
* Do not approve list endpoints without pagination "because the data is small today".
* Do not call a change non-breaking without checking every field and status code that clients see.
* Do not debate REST purity when the design is consistent and clear.
* Do not invent existing conventions; read them from the spec or code.

## Examples

**User:** "Review these new endpoints before we publish them."

```text
POST /api/v1/createInvoice          → 200 { "success": false, "error": "bad amount" }
GET  /api/v1/invoices?customer=12   → 200 [ ...all invoices... ]
PUT  /api/v1/invoices/{id}          → body: { "Amount": 12.5, "status": "Paid" }
```

**Expected output:**

```text
Existing conventions (from openapi.yaml): snake_case fields, plural resources, cursor pagination
({ data, next_cursor }), errors as { error: { code, message, fields } }, amounts in cents.

## Must fix
1. POST /createInvoice → POST /api/v1/invoices, return 201 + Location: /api/v1/invoices/{id}.
2. Errors returned with 200. Use 422 and the standard shape:
   { "error": { "code": "invalid_amount", "message": "...", "fields": { "amount": "must be > 0" } } }
3. GET /invoices returns every row. Add ?limit (default 50, max 200) and ?cursor; return
   { "data": [...], "next_cursor": "..." } like /customers does.
4. "Amount": 12.5 → "amount_cents": 1250, "currency": "USD". Floats lose cents.

## Should fix
5. Field casing: "Amount" / "status" → snake_case, lowercase enum values ("paid").
6. ?customer=12 → ?customer_id=12, matching /payments.
7. PUT replaces the whole invoice; if clients send partial updates, use PATCH.

## Consider
8. Accept an Idempotency-Key header on POST /invoices to make retries safe.
```
