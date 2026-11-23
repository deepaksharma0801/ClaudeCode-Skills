---
name: accessibility-audit
description: Audits a web page or UI component against WCAG 2.2 AA and returns located issues with code fixes. Use when asked to check accessibility, a11y, screen-reader or keyboard support, or color contrast.
---

# Detailed Instructions

Test what users actually hit: keyboard, screen reader semantics, contrast, and zoom. Every issue
names the element, the WCAG criterion, who it affects, and the code that fixes it.
Automated scanners find only part of accessibility problems; the rest — focus order, keyboard
traps, meaningless labels, unannounced errors — need a manual pass. Reporting a clean automated
scan as "accessible" is the most common mistake.

## When to Use

- "Is this page/component accessible?", WCAG or ADA/EAA compliance checks
- Reviewing forms, modals, menus, custom widgets, and charts
- Before launching a public page or design-system component
- A user complaint about keyboard or screen-reader use

**Don't use when:** the question is visual design taste with no accessibility angle (use
`chart-critique` for charts), or legal advice on compliance obligations (give the technical
findings and recommend legal review).

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

## Checklist

```text
- [ ] Scope and framework noted
- [ ] Automated pass (axe-core / Lighthouse) run and de-duplicated
- [ ] Keyboard: reach, operate, visible focus, logical order, no traps, Escape closes, focus returns
- [ ] Semantics: native elements, headings, landmarks, lists/tables
- [ ] Names: labels, icon buttons, alt text, link text
- [ ] Contrast computed: text 4.5:1 (3:1 large), UI/focus 3:1
- [ ] Dynamic content announced; errors linked to fields
- [ ] 200% zoom / 320px width; reduced motion; target size
- [ ] Each issue: severity, location, WCAG criterion, who's affected, code fix
- [ ] Passed checks and untested areas listed
```

## Red Flags

- "Lighthouse says 100, we're accessible."
- `<div onClick>` for buttons; `outline: none` globally.
- `aria-label` sprinkled everywhere instead of visible labels.
- Suggesting an accessibility overlay widget.

## Anti-Patterns (What NOT to do)

* Do not report a clean result from an automated scan alone as "accessible".
* Do not add ARIA roles to elements that already have native semantics, or `aria-label` that contradicts visible text.
* Do not fix focus problems by removing outlines or adding `tabindex` greater than 0.
* Do not guess contrast; compute it from the colors in the code.
* Do not suggest an accessibility overlay widget as a fix.

## Examples

### Example 1: a signup form

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

### Example 2: a custom modal

**User:** "Our confirm-delete modal is a div we show with CSS. Is it OK?"

**Expected output:**

```text
1. BLOCKER — 2.1.2 No keyboard trap / 2.4.3 Focus order — Modal.tsx
   Focus stays on the page behind; Tab moves through hidden content; Escape does nothing.
   Fix: use <dialog> with showModal() (built-in focus containment and Escape), or trap focus in
   the modal, move focus to its first control on open, and return it to the trigger on close.
2. SERIOUS — 4.1.2 Name, role, value — the div has no role or name.
   Fix: <dialog aria-labelledby="del-title"> … <h2 id="del-title">Delete project?</h2>
3. SERIOUS — background content still readable by screen readers while open.
   Fix: showModal() makes the rest inert; otherwise add the inert attribute to the page root.

Recommended rewrite:
<dialog ref={ref} aria-labelledby="del-title" onClose={onCancel}>
  <h2 id="del-title">Delete project?</h2>
  <p>This can't be undone.</p>
  <button onClick={onConfirm}>Delete</button>
  <button autoFocus onClick={() => ref.current.close()}>Cancel</button>
</dialog>
```

## Quick Reference

| Check | Pass condition |
|---|---|
| Keyboard | Everything reachable and operable; visible focus; no traps |
| Buttons/links | Native `<button>` / `<a href>` |
| Form fields | Visible `<label>`; errors via `aria-describedby` + announced |
| Images | Meaningful `alt`, or `alt=""` if decorative |
| Contrast | 4.5:1 text, 3:1 large text and UI |
| Modals | `<dialog>` + `showModal()`, focus returns on close |
| Zoom | Usable at 200% and 320px wide |
