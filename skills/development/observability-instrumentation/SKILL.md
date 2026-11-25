---
name: observability-instrumentation
description: Adds structured logs, metrics, and traces to a service so failures can be found and explained, using OpenTelemetry and RED metrics. Use when adding monitoring, logging, tracing, or alerts to code.
---

# Detailed Instructions

Instrument for the questions you will ask during an incident: is it broken, for whom, since when,
and where. Every log line should be searchable, every metric cheap to store, and every request
traceable across services.
Instrumentation you add during an outage is too late — and instrumentation that logs secrets or
explodes metric cardinality becomes its own incident.

## When to Use

- A service with little or no logging, metrics, or tracing
- "We couldn't tell what happened during the outage"
- Adding a new service, endpoint, queue consumer, or cron job
- Errors that can't be connected across services
- Designing alerts or SLOs

**Don't use when:** the task is reading existing logs to find a problem (use `log-triage`), or
finding why something is slow (use `performance-investigation` — it may then add instrumentation).

## Overview

Services usually log too much of the wrong thing (`print("here")`, full request bodies) and too
little of the right thing (request IDs, durations, outcomes). This skill adds structured logging
with correlation IDs, RED metrics (Rate, Errors, Duration) for every entry point, OpenTelemetry
tracing across boundaries, and a small set of symptom-based alerts.

## Workflow Rules

1. **Map the service:** entry points (HTTP routes, queue consumers, cron jobs), outbound calls
   (databases, APIs, queues), and the existing logging/metrics libraries. Extend what exists.
2. **Structured logs:**
   - JSON with consistent keys: `timestamp`, `level`, `message`, `service`, `trace_id`,
     `request_id`, plus event-specific fields (`order_id`, `duration_ms`, `status`).
   - One log per meaningful event (request completed, job failed), not per line of code.
   - Levels: ERROR = needs action, WARN = degraded but handled, INFO = business events,
     DEBUG = off in production.
   - Never log secrets, tokens, passwords, full card numbers, or request bodies with personal data.
3. **Metrics (RED)** per entry point: request count, error count (by type), and duration
   histogram, labeled by route template (`/orders/{id}`, not `/orders/123`), method, and status class.
   Keep label cardinality bounded — never label by user ID, email, or raw URL.
4. **Traces:** use OpenTelemetry auto-instrumentation for the framework, HTTP clients, and database
   drivers first; add manual spans only around important internal steps. Propagate context
   (`traceparent` header) across services and queues, and put `trace_id` in logs.
5. **Alerts** on symptoms users feel, tied to SLOs: error rate and latency for key routes, queue
   age for consumers, job success for crons. Each alert links to a runbook or dashboard. Avoid
   alerting on causes like CPU unless they predict user impact.
6. **Verify:** trigger a request and an error locally or in staging; show the log line, the metric,
   and the trace that result, connected by the same `trace_id`.

## Checklist

```text
- [ ] Entry points and outbound calls mapped; existing libraries identified
- [ ] JSON logs with timestamp, level, service, trace_id, request_id
- [ ] One log per meaningful event; levels used consistently
- [ ] No secrets, tokens, or personal data in logs
- [ ] RED metrics per entry point, labeled by route template, method, status class
- [ ] No unbounded labels (user ID, email, raw URL, error text)
- [ ] OpenTelemetry auto-instrumentation for framework, HTTP clients, DB drivers
- [ ] Trace context propagated across services and queues; trace_id in logs
- [ ] Symptom-based alerts with owner, threshold rationale, runbook link
- [ ] Verified: one request shows the same trace_id in log, metric exemplar/trace
```

## Red Flags

- A metric label containing user id, email, URL with ids, or request id.
- Logging whole request or response bodies "for debugging".
- `console.log` / `print` strings instead of structured fields.
- Adding traces without propagating context across service and queue boundaries.
- No alert or dashboard question behind a new metric.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "More logs are always better." | Unstructured volume costs money and buries the line you need. |
| "A user_id label is useful." | Unbounded label values explode metric cardinality and cost. |
| "We'll add tracing when there's an incident." | You can't trace an incident that already happened. |
| "Logging the payload is fine internally." | Logs are widely readable and retained; payloads leak secrets and PII. |

## Anti-Patterns (What NOT to do)

* Do not log full request or response bodies, headers with tokens, or personal data.
* Do not use unbounded metric labels (user IDs, raw paths, error messages).
* Do not add a manual span to every function; start with auto-instrumentation.
* Do not create alerts without an owner, a threshold rationale, and a runbook.
* Do not log and rethrow the same error at every layer; log it once where it is handled.

## Examples

### Example 1: a service with nothing

**User:** "Our FastAPI orders service has basically no observability. Add some."

**Expected output:**

```python
# app/telemetry.py
import time
import structlog
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_client import Counter, Histogram

def add_trace_ids(_, __, event):
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        event["trace_id"] = format(ctx.trace_id, "032x")
    return event

structlog.configure(processors=[
    structlog.contextvars.merge_contextvars, add_trace_ids,
    structlog.processors.add_log_level, structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.JSONRenderer()])
log = structlog.get_logger(service="orders")

REQUESTS = Counter("http_requests_total", "Requests", ["route", "method", "status_class"])
LATENCY = Histogram("http_request_duration_seconds", "Latency", ["route", "method"])

def instrument(app, engine):
    FastAPIInstrumentor.instrument_app(app)      # spans per request, traceparent propagation
    HTTPXClientInstrumentor().instrument()        # outbound calls
    SQLAlchemyInstrumentor().instrument(engine=engine)

    @app.middleware("http")
    async def red_metrics(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", "unmatched")  # set during routing; template, not raw path
        LATENCY.labels(route, request.method).observe(time.perf_counter() - start)
        REQUESTS.labels(route, request.method, f"{response.status_code // 100}xx").inc()
        log.info("request_completed", route=route, method=request.method, status=response.status_code)
        return response
```

```text
Alerts (Prometheus rules, linked to runbooks/orders.md)
- OrdersHighErrorRate: 5xx / all requests on /orders* > 2% for 5m
- OrdersSlow: p95 http_request_duration_seconds{route=~"/orders.*"} > 1s for 10m

Verified in staging: POST /orders → log line {"event":"request_completed","route":"/orders",
"status":201,"trace_id":"4bf9…"} → same trace_id in Jaeger shows FastAPI → SQLAlchemy INSERT →
httpx POST payments. Request bodies are not logged.
```

### Example 2: noisy logs that still don't help

**User:** "We log a ton but still can't debug anything. Here's a sample:
`INFO here`, `INFO got data {…full JSON body…}`, `ERROR Error: Error`."

**Expected output:**

```text
## What's wrong
- Unstructured strings: can't filter by order or customer.
- No request or trace ID: lines from concurrent requests interleave with no way to group them.
- Full request bodies logged: they include emails and addresses (personal data) and card
  last-4s; they also make up most of the log volume.
- "Error: Error": the exception type, message, and stack trace are lost.

## Changes
1. Switch to structured JSON logs with request_id + trace_id bound per request (middleware).
2. Replace debug breadcrumbs ("here", "got data") with one event per outcome:
   log.info("order_created", order_id=o.id, items=len(o.items), total_cents=o.total_cents)
3. Log exceptions once, where they're handled, with the stack:
   log.exception("payment_failed", order_id=o.id, provider="stripe")
4. Remove body logging; add a redaction processor that drops keys named password, token,
   authorization, card, email as a safety net.

Result in staging: log volume down 78%; searching order_id=81723 returns the 4 lines for that
order across API and worker, joined by one trace_id.
```

## Quick Reference

| Signal | Default |
|---|---|
| Logs | JSON; timestamp, level, service, trace_id, request_id + event fields |
| Levels | ERROR = action needed, WARN = degraded, INFO = business events, DEBUG off in prod |
| Metrics | RED per entry point; labels = route template, method, status class |
| Traces | OpenTelemetry auto-instrumentation first; propagate `traceparent` |
| Alerts | On user-facing symptoms (errors, latency, queue age) with runbooks |
| Never | Secrets/PII in logs; user IDs or raw URLs as metric labels |

