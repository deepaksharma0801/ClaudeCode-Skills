# What makes a skill good

The quality bar every skill in this repo is written and reviewed against. It is distilled from:

- Anthropic, [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- The [Agent Skills specification](https://agentskills.io/specification)
- [anthropics/skills — skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) and [mcp-builder](https://github.com/anthropics/skills/tree/main/skills/mcp-builder)
- [obra/superpowers — systematic-debugging and writing-skills](https://github.com/obra/superpowers/tree/main/skills)

## Contents

1. [The principle](#the-principle)
2. [Required sections](#required-sections)
3. [Writing the description](#writing-the-description)
4. [Degrees of freedom](#degrees-of-freedom)
5. [Red flags and rationalizations](#red-flags-and-rationalizations)
6. [Examples](#examples)
7. [Bundled files](#bundled-files)
8. [Evals](#evals)
9. [Review checklist](#review-checklist)

## The principle

A skill is worth loading only for what Claude does **not** already do reliably. Every paragraph
should change behavior: a decision rule, a step Claude tends to skip, a trap, a format, a command.
Thorough is good; padding is not. Explain *why* a rule exists — Claude follows reasons more
reliably than bare MUSTs, and a reason lets it handle cases the rule didn't anticipate.

Ask of every paragraph: *would Claude do this differently without it?* If not, cut it.

## Required sections

In this order. The validator enforces the five marked with *.

| Section | What it holds |
|---|---|
| `# Detailed Instructions` * | The core principle in 2–4 sentences, and why it matters |
| `## When to Use` | Concrete triggers and symptoms, plus **when not to use** it (and what to use instead) |
| `## Overview` * | The failure this skill prevents, and the approach in one paragraph |
| `## Workflow Rules` * | Phases or numbered steps. Each step: what to do, the exact command where it matters, and why |
| `## Checklist` | A copyable `- [ ]` list Claude can track progress with |
| `## Red Flags` | Thoughts or actions that mean the process is going wrong (for discipline skills) |
| `## Common Rationalizations` | Table of excuse → reality (for discipline skills) |
| `## Anti-Patterns (What NOT to do)` * | Each with a one-line *why* |
| `## Examples` * | At least two: a full worked example, plus an edge case or before/after |
| `## Quick Reference` | A compact table to scan once the skill is familiar |

Optional where useful: decision tables, a short Mermaid diagram for branching processes,
pointers to `references/` files.

## Writing the description

- Third person: "Reviews …", "Builds …" — never "I can help" or "You can use".
- What it does **and** when to use it, with the words users actually type (symptoms, tool names,
  file types). Claude tends to under-trigger skills, so name the situations generously.
- ≤ 200 characters in this repo (the spec allows 1,024). No unquoted `: ` (breaks YAML).
- Don't summarize the workflow in the description; Claude may follow the summary instead of
  reading the skill.

## Degrees of freedom

Match how prescriptive a step is to how fragile it is:

| Freedom | Form | Use for |
|---|---|---|
| High | Principles and heuristics | Judgment calls: reviews, writing, analysis |
| Medium | Patterns, pseudocode, parameterized commands | A preferred approach exists but context varies |
| Low | Exact commands or a bundled script, "run exactly this" | Fragile, destructive, or must-be-consistent steps |

Give **one default** with an escape hatch, not a menu of five equal options.

## Red flags and rationalizations

For skills that enforce a discipline (debugging, testing, migrations, security), the failure is
usually Claude knowing the rule and skipping it under pressure. Close those loopholes explicitly:

- **Red Flags:** the thoughts that precede a bad shortcut ("just try X and see").
- **Common Rationalizations:** a table of the excuse and why it's wrong.

For skills about output shape (writing, reports), prefer a positive recipe — "the output is these
parts, in this order" — over a list of prohibitions; prohibitions invite negotiation.

## Examples

- One excellent, realistic example beats several thin ones. Use real-looking data, not `foo/bar`.
- Show the exact output format when format matters.
- Add a second example that covers an edge case, a "before → after", or the case where the right
  answer is "don't do it".
- Numbers in examples must be internally consistent (recompute them).

## Bundled files

- `scripts/` for deterministic steps; standard library only where possible; clear errors.
- `references/` for depth Claude needs only sometimes (long checklists, per-framework variants).
  Keep them one level deep from `SKILL.md`; give files over 100 lines a table of contents.
- `SKILL.md` stays under 500 lines.
- Forward slashes in paths; no time-sensitive statements ("before August 2025…").

## Evals

`evals/evals.json` with at least three realistic prompts, including one that tempts the exact
failure the skill exists to prevent. Each has `expected_output` and checkable `expectations`.

## Review checklist

- [ ] Description: third person, what + when, ≤ 200 chars, valid YAML
- [ ] Core principle stated with its reason
- [ ] When to use **and** when not to use
- [ ] Steps say why, and give exact commands where fragile
- [ ] Copyable checklist
- [ ] Red flags + rationalizations (discipline skills) or a positive output recipe (shape skills)
- [ ] Anti-patterns each have a why
- [ ] Two or more examples, numbers verified
- [ ] Quick reference table
- [ ] ≥ 3 evals, one targeting the main failure mode
- [ ] Under 500 lines; `python3 scripts/validate_skills.py` passes
