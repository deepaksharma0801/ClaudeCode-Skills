---
name: error-handling-review
description: Reviews error handling for swallowed exceptions, unsafe retries, missing timeouts, leaked details, and partial failures. Use when reviewing code that calls networks, databases, queues, or files.
---

# Detailed Instructions

For every operation that can fail, ask four questions: is the failure **noticed** (not
swallowed), **handled at the right level** (by code that can actually do something about it),
**bounded** (timeouts and retry limits), and **reported** usefully (logs for operators, a safe
message for users)? Most production incidents in error paths come from a `catch` that hides a
failure, a retry that has no limit, or a call that has no timeout.

## When to Use

- Reviewing code that calls HTTP APIs, databases, queues, caches, or the file system
- "Why did this fail silently?" / "why did one slow dependency take everything down?"
- Adding retries, timeouts, or circuit breakers
- Reviewing API error responses for consistency and leaks

**Don't use when:** the task is finding a specific bug's cause (use `root-cause-debugging`), or
the question is about what to log and measure in general (use `observability-instrumentation`).

## Overview

Error-handling code is the least tested code in most systems, and it runs exactly when things are
already going wrong. This skill lists the failure points in the change, checks each against a
fixed set of rules (no swallowing, catch narrowly, timeouts everywhere, bounded idempotent
retries, clean partial-failure state, safe messages), and gives fixes in the codebase's own
idiom.

## Workflow Rules

1. **List failure points:** every network call, DB query, file operation, parse, and
   third-party SDK call in the change.
2. **No swallowing:** flag `except: pass`, `catch (e) {}`, `catch` that only logs and then continues
   as if the operation succeeded, and `_ = err` in Go. Either handle it, or let it propagate.
3. **Catch narrowly, at the right level:** catch the specific exception the code can handle
   (`requests.Timeout`, `IntegrityError`), not `Exception`, and only where there's a real
   response (retry, fallback, user message). Otherwise let it bubble to a top-level handler.
4. **Timeouts on every external call:** HTTP clients (`requests` has no default timeout), DB
   statement timeouts, queue receives. Timeouts should fit inside the caller's own deadline.
5. **Retries:** only for transient errors (timeouts, 429, 503), with exponential backoff +
   jitter, a max attempt count, and only for **idempotent** operations — or with an idempotency
   key. Honor `Retry-After`. Never retry 4xx validation errors.
6. **Partial failure:** if step 2 of 3 fails, what state is left? Use transactions, the outbox
   pattern, or compensating actions, and make operations safe to re-run.
7. **Preserve context:** wrap with context (`raise … from e`, `fmt.Errorf("charge %s: %w", id, err)`,
   `new Error(msg, { cause })`), and log once at the boundary with structured fields — not at
   every layer.
8. **Safe messages:** users and API clients get a stable error code and a helpful message, never
   stack traces, SQL, or internal hostnames. Operators get the details in logs.
9. **Resource cleanup:** `with`/`using`/`defer`/`finally` for files, connections, and locks on
   every path.

## Checklist

```text
- [ ] Every failure point listed
- [ ] No swallowed errors; no "log and continue as success"
- [ ] Narrow catches, at a level that can act
- [ ] Timeouts on every external call, within the caller's deadline
- [ ] Retries: transient only, backoff + jitter, capped, idempotent
- [ ] Partial-failure state is consistent or recoverable
- [ ] Errors wrapped with context; logged once
- [ ] User-facing errors safe and stable; details only in logs
- [ ] Resources released on all paths
```

## Red Flags

- `except Exception: pass` or an empty `catch`.
- `requests.get(url)` with no `timeout=`.
- `while True: try … except: sleep(1)` retry loops.
- Retrying a `POST /charge` without an idempotency key.
- `return res.status(500).send(err.stack)`.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "It rarely fails." | Rare failures without handling become silent data loss. |
| "Retrying makes it more reliable." | Unbounded retries amplify outages and duplicate side effects. |
| "The library has a default timeout." | Many don't (`requests`, many DB drivers); set it explicitly. |
| "Logging at every layer helps debugging." | It produces duplicate noise; wrap with context, log once. |

## Anti-Patterns (What NOT to do)

* **Catching `Exception` to keep going** — hides bugs and corrupts state.
* **Returning `None`/`null` on failure** — callers forget to check; raise or return an explicit result type.
* **Retrying non-idempotent operations blindly** — double charges, duplicate emails.
* **Exposing internals in error responses** — helps attackers, confuses users.
* **Inconsistent error shapes across endpoints** — clients can't handle errors generically.

## Examples

### Example 1: a payment call

**User:** "Review this."

```python
def charge(order):
    for _ in range(5):
        try:
            r = requests.post(PAY_URL, json={"amount": order.total, "card": order.card_token})
            order.status = "paid"
            db.save(order)
            return r.json()
        except Exception as e:
            log.error(e)
            time.sleep(1)
```

**Expected output:**

```markdown
1. **Double-charge risk — High.** Retries a non-idempotent POST: a timeout after the provider
   charged leads to another charge. Fix: send an idempotency key (`Idempotency-Key: order.id`)
   and retry only on timeouts / 429 / 5xx.
2. **No timeout — High.** `requests` waits forever by default. Fix: `timeout=(3, 10)`.
3. **Marks paid without checking the response — High.** A 402 decline still sets `paid`.
   Fix: `r.raise_for_status()` before updating status.
4. **Swallows everything, returns None after 5 tries — Medium.** Callers can't tell failure from
   success. Fix: catch `requests.Timeout`/`ConnectionError` only, then raise `PaymentError`.
5. **Fixed 1 s sleep — Low.** Use exponential backoff with jitter, max 3 attempts.

    for attempt in range(3):
        try:
            r = requests.post(PAY_URL, json=payload, timeout=(3, 10),
                              headers={"Idempotency-Key": str(order.id)})
            if r.status_code in (429, 502, 503, 504):
                raise TransientError(r.status_code)
            r.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError, TransientError) as e:
            if attempt == 2:
                raise PaymentError(f"charge {order.id} failed") from e
            time.sleep(min(8, 2 ** attempt) + random.random())
    order.status = "paid"; db.save(order)
```

### Example 2: an error that leaks

**User:** "Our API returns `{"error": "duplicate key value violates unique constraint
\"users_email_key\""}`. OK?"

**Expected output:**

```text
It leaks schema details and isn't stable for clients. Map known errors to a stable shape and
log the original:
  409 {"error": {"code": "email_taken", "message": "An account with this email already exists."}}
Catch IntegrityError at the API boundary, check the constraint name, and log the full exception
with a request id. Unknown errors → 500 {"error": {"code": "internal", "request_id": "…"}}.
```

## Quick Reference

| Rule | Example |
|---|---|
| Don't swallow | No empty `catch`; re-raise or handle |
| Catch narrowly | `except requests.Timeout` |
| Always time out | `requests.post(..., timeout=(3, 10))` |
| Retry safely | Transient only, backoff + jitter, cap, idempotency key |
| Partial failure | Transaction, outbox, or compensation |
| Keep context | `raise X from e`, `%w`, `{ cause }` |
| Safe messages | Stable code + message; details in logs |
