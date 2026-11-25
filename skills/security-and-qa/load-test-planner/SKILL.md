---
name: load-test-planner
description: Plans and writes k6 load tests with a realistic traffic model, pass/fail thresholds, ramp stages, and bottleneck analysis. Use before a launch or when asked if the system can handle N users.
compatibility: Examples use k6 (JavaScript). The method applies to Locust, Gatling, and JMeter.
---

# Detailed Instructions

A load test answers a specific question — "can checkout handle 3× Black Friday peak with p95
under 800 ms?" — so start from the target and the traffic model, not the tool. Model what real
users do (mix of endpoints, think time, data variety), set pass/fail thresholds before running,
ramp up instead of slamming, and watch the server side while it runs. The client's numbers
show that something broke; only server metrics show the bottleneck.

## When to Use

- "Can we handle N users / requests per second?"
- Before a launch, a marketing push, a seasonal peak, or a big customer onboarding
- After an architecture change (new database, caching, autoscaling) to confirm capacity
- Writing a k6/Locust script for a CI performance gate

**Don't use when:** one known endpoint is slow for single requests (use
`performance-investigation` — profile it first), or the goal is to test resilience to failures
(that's chaos/fault injection, a different plan).

## Overview

Bad load tests hammer one endpoint with no think time from a laptop, report an average, and
conclude either "fine" or "slow" without knowing why. This skill derives the target load from
real traffic, writes a scenario that mirrors user behavior with varied test data, defines SLO-
based thresholds, picks the right test type (smoke, load, stress, soak, spike), runs it against a
production-like environment, and correlates client results with server metrics to name the
bottleneck.

## Workflow Rules

### 1. Define the question and target

1. Write the **goal**: the load (requests/s or concurrent users), the duration, and pass
   criteria from the SLO (p95/p99 latency, error rate). Derive load from data: current peak RPS
   from metrics × expected growth × safety margin.
2. Pick the **test type**:

| Type | Shape | Answers |
|---|---|---|
| Smoke | 1–2 VUs, 1 min | Does the script work? Run first, always |
| Load | Ramp to target, hold 15–30 min | Does it meet SLOs at expected peak? |
| Stress | Keep ramping past target | Where and how does it break? |
| Spike | Jump to peak instantly | Does autoscaling / queueing cope? |
| Soak | Target load for hours | Leaks, connection exhaustion, disk growth |

### 2. Model the traffic

3. Take the **endpoint mix** from access logs or APM (e.g. 60% browse, 25% search, 10% cart,
   5% checkout). Include think time between steps.
4. **Vary data:** many users, products, and search terms, so caches see a realistic hit rate. One
   repeated request measures the cache, not the system.
5. Use an **arrival-rate** executor (`constant-arrival-rate`, `ramping-arrival-rate`) when the
   target is requests/s — it keeps sending at the planned rate even when the server slows down,
   which is how real traffic behaves.

### 3. Environment and safety

6. Test a production-like environment (same instance sizes, data volume, config). Never load-test
   production or third-party APIs without explicit approval; stub payment providers and email.
7. Make sure the load generator isn't the bottleneck (watch its CPU; use distributed or cloud
   runners for high load).

### 4. Run and observe

8. Run smoke → load → (stress/spike/soak as needed). Set **thresholds** in the script so the
   run passes or fails on its own.
9. Watch server metrics during the run: CPU, memory, DB connections and slow queries, queue
   depth, GC pauses, autoscaling events, error logs. Note the time the first metric saturated.

### 5. Report

10. Report pass/fail per threshold, the **knee** (load where latency starts climbing), the
    bottleneck with evidence, and the next fix. Report percentiles, never just averages.

## Checklist

```text
- [ ] Goal: load, duration, SLO thresholds, derived from real traffic
- [ ] Test type chosen; smoke run first
- [ ] Endpoint mix and think time from logs/APM
- [ ] Varied test data; realistic cache behavior
- [ ] Arrival-rate executor when targeting RPS
- [ ] Production-like env; third parties stubbed; approval if shared infra
- [ ] Load generator not saturated
- [ ] Thresholds in the script; server metrics watched
- [ ] Report: pass/fail, knee, bottleneck + evidence, next fix
```

## Red Flags

- Reporting average latency only.
- One URL with one ID in a tight loop.
- "We'll run it against prod at night."
- The load generator's CPU at 100%.
- Concluding "the app is slow" without a server-side metric.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Staging is smaller, we'll extrapolate." | Bottlenecks (DB locks, pool sizes) don't scale linearly. Match production or label the result. |
| "Average latency looks fine." | Averages hide the tail that users feel; use p95/p99. |
| "VUs = users." | Without think time, 100 VUs can be thousands of real users' worth of load. |
| "No errors, so we passed." | Check latency thresholds too; timeouts may hide behind retries. |

## Anti-Patterns (What NOT to do)

* **Load-testing third-party APIs or production without approval** — you may cause the outage you're testing for.
* **Closed-loop VU tests when the goal is RPS** — load drops as the server slows, which hides the problem.
* **Skipping the smoke run** — a broken script produces nonsense numbers at scale.
* **One giant run with no ramp** — you can't see where it started degrading.
* **No thresholds** — results become a matter of opinion.

## Examples

### Example 1: Black Friday checkout capacity

**User:** "Peak last Black Friday was 400 req/s. Expect 2× this year. p95 SLO is 800 ms. Write the
k6 test."

**Expected output:**

```javascript
// loadtest/black-friday.js — target 800 rps (2× last peak); stress past it to 1,200
import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const products = new SharedArray('products', () => JSON.parse(open('./products.json'))); // 5,000 ids
const BASE = __ENV.BASE_URL; // staging, sized like prod

export const options = {
  scenarios: {
    browse: {
      executor: 'ramping-arrival-rate', exec: 'browse',
      startRate: 50, timeUnit: '1s', preAllocatedVUs: 400, maxVUs: 2000,
      stages: [
        { target: 680, duration: '10m' },  // ramp to 85% of 800
        { target: 680, duration: '20m' },  // hold
        { target: 1020, duration: '10m' }, // stress to 1.5x target
      ],
    },
    checkout: {
      executor: 'ramping-arrival-rate', exec: 'checkout',
      startRate: 5, timeUnit: '1s', preAllocatedVUs: 100, maxVUs: 500,
      stages: [
        { target: 120, duration: '10m' },  // 15% of 800
        { target: 120, duration: '20m' },
        { target: 180, duration: '10m' },
      ],
    },
  },
  thresholds: {
    'http_req_duration{scenario:checkout}': ['p(95)<800'],
    'http_req_duration{scenario:browse}': ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export function browse() {
  const id = products[Math.floor(Math.random() * products.length)];
  const r = http.get(`${BASE}/api/products/${id}`, { tags: { name: 'product' } });
  check(r, { '200': (res) => res.status === 200 });
  sleep(Math.random() * 3 + 1);
}

export function checkout() {
  const id = products[Math.floor(Math.random() * products.length)];
  const cart = http.post(`${BASE}/api/cart`, JSON.stringify({ productId: id, qty: 1 }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'cart' } });
  check(cart, { 'cart 201': (r) => r.status === 201 });
  const pay = http.post(`${BASE}/api/checkout`, JSON.stringify({ cartId: cart.json('id'),
    paymentToken: 'tok_visa' }), // payment provider in test mode / stubbed
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'checkout' } });
  check(pay, { 'paid 200': (r) => r.status === 200 });
}
```

Mix (85% browse / 15% checkout) comes from last November's APM data. Run
`k6 run -e BASE_URL=https://staging.example.com loadtest/black-friday.js` after a 1-VU smoke run,
with the DB, cache, and autoscaling dashboards open.

### Example 2: reading the results

**User:** "p95 was fine until ~650 rps, then checkout p95 jumped to 4s and errors hit 6%. App CPU
was 45%."

**Expected output:**

```text
The app servers weren't the limit (45% CPU). The knee at ~650 rps plus a sudden jump (not a gradual
climb) points to a fixed-size pool running out. Check, for the same time window:
1. DB connection pool: active = max? Waiting acquisitions? (most likely)
2. DB: CPU, lock waits, slow query log for the checkout inserts.
3. Payment stub latency — if it slowed, checkout threads stayed busy longer than usual.
Result: FAIL at 800 rps target (checkout p95 4s > 800 ms; errors 6% > 1%). Fix the bottleneck
you find, then rerun the same test to confirm the knee moves past 800.
```

## Quick Reference

| Item | Rule |
|---|---|
| Target | Real peak × growth × margin |
| First run | Smoke, 1 VU |
| RPS goals | Arrival-rate executors |
| Realism | Endpoint mix from logs, think time, varied data |
| Pass/fail | Thresholds in the script: p95/p99 + error rate |
| Observe | Server metrics, not just client |
| Report | Pass/fail, knee, bottleneck + evidence, next fix |
