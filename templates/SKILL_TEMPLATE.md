---
name: your-skill-name
description: Third person. What the skill does and when Claude should use it, with the words users actually type. Max 200 characters.
compatibility: Optional. Delete this line unless the skill needs specific tools, e.g. "Requires Python 3.8+ with pandas."
---

# Detailed Instructions

[The core principle in 2–4 sentences, and why it matters. See docs/QUALITY.md.]

## When to Use

- [Concrete trigger or symptom]
- [Another trigger]

**Don't use when:** [the case this skill is wrong for, and what to do instead]

## Overview

[The failure this skill prevents, and the approach in one paragraph.]

## Workflow Rules

### 1. [Phase name]

1. **[Step]** — what to do, the exact command if it matters, and why.
2. **[Step]** — …

### 2. [Phase name]

…

## Checklist

```text
- [ ] Step one
- [ ] Step two
```

## Red Flags

[Discipline skills: thoughts that mean the process is going wrong. Output-shape skills: delete
this section and Common Rationalizations; give a positive output recipe in Workflow Rules instead.]

- "[A thought that precedes a bad shortcut]"

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "[excuse]" | [why it's wrong] |

## Anti-Patterns (What NOT to do)

* **[Anti-pattern]** — why it's harmful.

## Examples

### Example 1: [realistic scenario]

**User:** "[request]"

**Expected output:**

```text
[exact output]
```

### Example 2: [edge case, before/after, or "don't do it" case]

…

## Quick Reference

| Situation | Do |
|---|---|
| [situation] | [action] |
