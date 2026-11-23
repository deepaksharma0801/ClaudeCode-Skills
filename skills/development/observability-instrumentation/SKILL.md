---
name: observability-instrumentation
description: Adds structured logs, metrics, and traces to a service so failures can be found and explained, using OpenTelemetry and RED metrics. Use when adding monitoring, logging, tracing, or alerts to code.
---

# Detailed Instructions

Instrument for the questions you will ask during an incident: is it broken, for whom, since when,
and where. Every log line should be searchable, every metric cheap to store, and every request
traceable across services.

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

## Anti-Patterns (What NOT to do)

* Do not log full request or response bodies, headers with tokens, or personal data.
* Do not use unbounded metric labels (user IDs, raw paths, error messages).
* Do not add a manual span to every function; start with auto-instrumentation.
* Do not create alerts without an owner, a threshold rationale, and a runbook.
* Do not log and rethrow the same error at every layer; log it once where it is handled.

## Examples

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
