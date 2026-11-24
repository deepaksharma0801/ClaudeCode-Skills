---
name: e2e-test-writer
description: Writes reliable Playwright end-to-end tests for critical user flows with role-based locators, web-first assertions, and isolated test data. Use when adding browser tests or fixing brittle UI tests.
compatibility: Examples use Playwright Test (TypeScript). The principles apply to Cypress and Playwright for Python.
---

# Detailed Instructions

Test a few critical user journeys end to end, the way a user would: find elements by role and
accessible name, wait with web-first assertions instead of sleeps, and give every test its own
data so tests can run in any order and in parallel. E2E tests are the slowest and flakiest layer;
each one has to earn its place, and any test that fails randomly gets ignored, along with the
real failures.

## When to Use

- "Add an E2E / browser / Playwright test for signup, checkout, login…"
- Covering a critical flow that unit tests can't (real browser, routing, auth, payments sandbox)
- Rewriting brittle tests that use CSS selectors, XPath, or `waitForTimeout`
- Setting up Playwright in a project for the first time

**Don't use when:** deciding *what* to test across all levels (use `test-plan-writer` first), a test
already fails intermittently and needs diagnosis (use `flaky-test-investigator`), or the behavior
can be tested at the unit or API level (test it there — faster and more stable).

## Overview

Brittle E2E suites come from the same few habits: selectors tied to markup, fixed sleeps, tests
that depend on each other or on shared seed data, and logging in through the UI in every test.
This skill picks the flows worth an E2E test, writes them with Playwright's resilient locators and
auto-waiting assertions, sets up auth once and reuses it, creates data per test through the API,
and runs the tests repeatedly to prove they're stable before calling them done.

## Workflow Rules

### 1. Choose what to test

1. **Only critical journeys:** the flows where a break costs money or users — signup, login,
   checkout, the core create/edit action. Aim for a handful, not hundreds. Edge cases and
   validation rules belong in unit or API tests.
2. Write each test as a user story: start state → actions → the outcome a user would see.

### 2. Set up

3. If Playwright isn't installed: `npm init playwright@latest`. In `playwright.config.ts` set
   `baseURL`, `trace: 'on-first-retry'`, `retries: process.env.CI ? 2 : 0`, and a `webServer` that
   starts the app. Retries capture traces; they don't excuse flakiness.
4. **Authenticate once:** a setup project logs in and saves `storageState` to
   `playwright/.auth/user.json` (gitignored); tests reuse it. Only the login test itself goes
   through the login UI.
5. **Test data per test:** create what the test needs through the API or a fixture
   (`request.post('/api/projects', …)`) with unique names (`Project ${testInfo.testId}`), and clean
   up in a fixture teardown. Never depend on data another test created.

### 3. Write the test

6. **Locators, in this order:** `getByRole` with name → `getByLabel` → `getByText` →
   `getByTestId` (add `data-testid` only when nothing accessible exists). No CSS chains, XPath, or
   `nth()` on layout. Role locators also catch accessibility regressions.
7. **Assertions are web-first:** `await expect(locator).toBeVisible()`, `toHaveText`, `toHaveURL`
   — they retry until the timeout. Never `waitForTimeout`, and never `expect(await
   locator.isVisible()).toBe(true)` (checks once, no retry).
8. Wait on outcomes, not time: for network-driven UI, assert the resulting UI, or
   `page.waitForResponse` for the specific call when there's no visible change.
9. **Stub only what you don't own** (third-party payment UI, email, analytics) with
   `page.route` or a sandbox; keep your own backend real, or it's not an E2E test.
10. Use `test.step` for readable reports on long flows.

### 4. Prove it's stable

11. Run it repeatedly before declaring done:
    `npx playwright test path/to.spec.ts --repeat-each=10 --workers=4`. Any failure is a bug in the
    test (or the app): fix it, don't add a retry.
12. On failure, read the trace (`npx playwright show-trace`) instead of guessing.

## Checklist

```text
- [ ] Flow is a critical journey; edge cases pushed down to unit/API tests
- [ ] Config: baseURL, webServer, trace on retry, CI retries
- [ ] Auth via saved storageState; UI login only in the login test
- [ ] Data created per test via API with unique names; cleaned up
- [ ] Locators: role/label/text first; test ids only when needed
- [ ] Web-first assertions; no waitForTimeout
- [ ] Only third-party services stubbed
- [ ] Passed --repeat-each=10 in parallel
```

## Red Flags

- `await page.waitForTimeout(2000)` "to let it load".
- Selectors like `div.card > .btn-primary:nth-child(2)`.
- Test B only passes after test A runs.
- Every test clicking through the login form.
- Raising the global timeout or adding retries to make a test pass.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "A short sleep is simpler." | It's slow when the app is fast and flaky when it's slow. Assert the outcome. |
| "Test IDs everywhere is most stable." | Role locators are equally stable and test what users and screen readers see. |
| "Shared seed data is faster." | Shared data makes tests order-dependent and breaks parallel runs. |
| "Retries handle flakiness." | Retries hide it until real failures get dismissed too. |

## Anti-Patterns (What NOT to do)

* **Testing every validation rule through the browser** — slow; do it at unit/API level.
* **Mocking your own backend in E2E** — you end up testing the mocks.
* **Asserting on implementation details** (class names, internal state) — breaks on harmless refactors.
* **One giant test covering five flows** — one failure hides the rest; split by journey.
* **Committing `storageState` files** — they contain live session tokens.

## Examples

### Example 1: checkout happy path

**User:** "Write a Playwright test for checkout: add a product to the cart, pay with the test card,
see the confirmation."

**Expected output:**

```ts
// tests/checkout.spec.ts
import { test, expect } from '@playwright/test';

test.use({ storageState: 'playwright/.auth/user.json' });

test('customer can buy a product', async ({ page, request }, testInfo) => {
  // Arrange: a product only this test uses
  const name = `E2E Mug ${testInfo.testId}`;
  const res = await request.post('/api/test/products', { data: { name, priceCents: 1200 } });
  const product = await res.json();

  await test.step('add to cart', async () => {
    await page.goto(`/products/${product.slug}`);
    await page.getByRole('button', { name: 'Add to cart' }).click();
    await expect(page.getByRole('link', { name: /cart \(1\)/i })).toBeVisible();
  });

  await test.step('pay', async () => {
    await page.getByRole('link', { name: /cart/i }).click();
    await page.getByRole('button', { name: 'Checkout' }).click();
    const card = page.frameLocator('iframe[title="Secure card payment input frame"]');
    await card.getByPlaceholder('Card number').fill('4242 4242 4242 4242');
    await card.getByPlaceholder('MM / YY').fill('12 / 34');
    await card.getByPlaceholder('CVC').fill('123');
    await page.getByRole('button', { name: 'Pay $12.00' }).click();
  });

  await expect(page).toHaveURL(/\/orders\/\w+/);
  await expect(page.getByRole('heading', { name: 'Thanks for your order' })).toBeVisible();
  await expect(page.getByText(name)).toBeVisible();
});
```

Notes: uses Stripe's published test card in its sandbox (no real charge); the product comes from a
test-only API route that exists only outside production; checked with `--repeat-each=10`.

### Example 2: fixing a brittle test

**User:** "This test fails randomly in CI."

```ts
await page.click('#app > div.main > form button.btn-primary');
await page.waitForTimeout(3000);
expect(await page.isVisible('.toast-success')).toBe(true);
```

**Expected output:**

```ts
await page.getByRole('button', { name: 'Save changes' }).click();
await expect(page.getByRole('status')).toHaveText('Settings saved');
```

Why it was flaky: the 3 s sleep is too short when CI is slow, and `isVisible` checks once without
retrying. The web-first assertion retries until the toast appears (up to the expect timeout), and
the role locator survives markup changes. If the toast has no `role="status"`, add it — that also
fixes a screen-reader issue.

## Quick Reference

| Need | Use |
|---|---|
| Find an element | `getByRole('button', { name: 'Save' })`, `getByLabel('Email')` |
| Wait for UI | `await expect(locator).toBeVisible()` / `toHaveText()` |
| Wait for a call | `page.waitForResponse(r => r.url().includes('/api/save'))` |
| Log in once | Setup project + `storageState` |
| Test data | API call per test, unique name, teardown |
| Stub third parties | `page.route('**/analytics/**', r => r.fulfill({ status: 204 }))` |
| Prove stability | `--repeat-each=10 --workers=4` |
| Debug a failure | `npx playwright show-trace trace.zip` |
