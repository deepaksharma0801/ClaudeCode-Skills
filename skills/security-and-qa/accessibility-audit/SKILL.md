---
name: accessibility-audit
description: Audits a web page or UI component against WCAG 2.2 AA and returns located issues with code fixes. Use when asked to check accessibility, a11y, screen-reader or keyboard support, or color contrast.
---

# Detailed Instructions

Test what users actually hit: keyboard, screen reader semantics, contrast, and zoom. Every issue
names the element, the WCAG criterion, who it affects, and the code that fixes it.

## Overview

Automated scanners find roughly a third of accessibility problems. This skill combines an automated
pass (when tools are available) with a manual checklist that covers what scanners miss — focus
order, keyboard traps, meaningful labels, and announcements for dynamic content.

## Workflow Rules

1. **Scope:** the page, route, or component, and the framework (React, Vue, plain HTML).
2. **Automated pass:** if a browser or Node is available, run axe-core (`@axe-core/cli`,
   `@axe-core/playwright`) or Lighthouse accessibility. Include its findings, de-duplicated.
3. **Manual checklist:**
   - **Keyboard:** every interactive element reachable with Tab, operable with Enter/Space,
     visible focus indicator, logical order, no traps, Escape closes dialogs, focus returns after.
   - **Semantics:** native elements over `div` + click handlers; one `h1` and no skipped heading
     levels; landmarks (`main`, `nav`); lists and tables marked up as such.
   - **Names:** every input has a programmatic label; icon buttons have `aria-label`; images have
     meaningful `alt` or `alt=""` if decorative; links describe their destination.
   - **Contrast:** text 4.5:1 (3:1 for large text), UI components and focus rings 3:1. Compute
     ratios from the actual colors.
   - **Dynamic content:** errors and toasts announced (`aria-live`, `role="alert"`); form errors
     linked with `aria-describedby`; loading states communicated.
   - **Zoom and motion:** usable at 200% zoom and 320px width without horizontal scroll; respects
     `prefers-reduced-motion`; target size at least 24x24 px.
4. **Report** each issue: severity (blocker / serious / moderate), element or `file:line`, WCAG
   criterion number, who is affected, and a code fix.
5. Prefer fixing with native HTML before adding ARIA.
6. List what was checked and passed, and what could not be tested (e.g. no screen reader available).

## Anti-Patterns (What NOT to do)

* Do not report a clean result from an automated scan alone as "accessible".
* Do not add ARIA roles to elements that already have native semantics, or `aria-label` that contradicts visible text.
* Do not fix focus problems by removing outlines or adding `tabindex` greater than 0.
* Do not guess contrast; compute it from the colors in the code.
* Do not suggest an accessibility overlay widget as a fix.

## Examples

**User:** "Can you check the signup form for accessibility?"

**Expected output:**

```text
Scope: src/components/SignupForm.tsx (React). axe-core: 3 violations. Manual: 3 more.

## Issues
1. BLOCKER — 2.1.1 Keyboard — SignupForm.tsx:58
   "Show password" is a <div onClick>; keyboard users cannot reach it.
   Fix: <button type="button" aria-pressed={shown} aria-label="Show password">

2. SERIOUS — 1.3.1 / 4.1.2 Name — SignupForm.tsx:31, 39
   Email and password inputs use placeholder text only; screen readers announce "edit text".
   Fix: <label htmlFor="email">Email</label> (visible), keep placeholder optional.

3. SERIOUS — 1.4.3 Contrast — signup.css:12
   Helper text #9CA3AF on #FFFFFF = 2.5:1 (needs 4.5:1).
   Fix: #6B7280 (4.8:1).

4. SERIOUS — 3.3.1 Error identification — SignupForm.tsx:72
   Errors appear in red text but are not announced or linked to the field.
   Fix: aria-invalid="true", aria-describedby="email-error", and role="alert" on the message.

5. MODERATE — 2.4.7 Focus visible — globals.css:4
   `*:focus { outline: none }` removes focus rings site-wide.
   Fix: replace with :focus-visible { outline: 2px solid #2563EB; outline-offset: 2px }

## Passed
Tab order follows visual order; submit works with Enter; page has one h1; usable at 200% zoom.

## Not tested
Screen reader output was not checked live (no VoiceOver/NVDA session available).
```
