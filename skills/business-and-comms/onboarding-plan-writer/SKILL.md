---
name: onboarding-plan-writer
description: Writes a 30/60/90-day onboarding plan for a new hire with week-one setup, a first shipped task, named contacts, and checkable milestones. Use when a manager is preparing for a new team member.
---

# Detailed Instructions

Plan for the new hire to **ship something small in week one** and own something meaningful by
day 90, with every week having a concrete goal and a named person to ask. Onboarding fails
when it's a reading list and "shadow people": the new hire feels useless, and the manager has no
signal until a rough review months later. Concrete milestones give both of them early, honest
feedback.

## When to Use

- "Write an onboarding plan for my new backend engineer / analyst / PM"
- Preparing week one: access, setup, buddy, first task
- Turning tribal knowledge into a repeatable onboarding doc
- A new hire is struggling and the plan needs resetting

**Don't use when:** the new hire needs a technical map of the codebase (use
`codebase-onboarding` and link it from the plan), or the task is hiring itself (use
`job-description-writer` / `interview-scorecard-writer`).

## Overview

Good onboarding has three parts: logistics done before day one, a first win in week one, and
outcomes that grow in scope by 30, 60, and 90 days. This skill gathers the role, team,
systems, and the first real projects from the manager, then writes a plan with a pre-day-one
checklist, a day-by-day first week, 30/60/90 outcomes that can be checked, named contacts, and
check-in points, leaving placeholders instead of inventing names or projects.

## Workflow Rules

1. **Gather:** role and level, team mission, the systems and tools they'll use, who the buddy is,
   2–3 real starter tasks, the main 90-day project, key people to meet, and any rituals (standup,
   on-call, planning). Use `<TODO>` for anything not given — never invent names or projects.
2. **Before day one:** laptop, accounts and access requests (these take days), calendar invites
   for rituals and 1:1s, a buddy assigned, the starter task prepared (scoped, with context and a
   reviewer).
3. **Week one, day by day:** day 1 is setup and people, not reading; by day 2–3 the local
   environment runs; by day 5 the first small change is merged (a bug fix, a docs fix, a small
   test). Each day has 1–2 goals.
4. **30 / 60 / 90 outcomes**, each checkable:
   - **30 days — learn and contribute:** several small changes shipped, can run and deploy the
     service, has met key people, joined on-call shadowing if relevant.
   - **60 days — own a piece:** delivers a medium-sized feature or fix end to end with support;
     reviews others' code.
   - **90 days — own an area:** leads a project or owns a component; contributes to planning;
     on-call primary if the role includes it.
5. **People to meet:** a table with name/role, why they matter, and when.
6. **Check-ins:** weekly 1:1, plus explicit reviews at 30, 60, and 90 days against the outcomes,
   where both sides say what's working. Ask the new hire to fix one thing in the onboarding doc
   — they see gaps nobody else does.
7. Keep it to one or two pages; link out to docs, runbooks, and `codebase-onboarding` maps.

## Output shape

```markdown
# Onboarding: <name>, <role> — starts <date>
Manager · Buddy
## Before day one      access, equipment, invites, starter task ready
## Week one            day 1–5 goals
## 30 / 60 / 90 days   checkable outcomes
## People to meet      who · why · when
## Check-ins           weekly 1:1 + 30/60/90 reviews
## Resources           links
```

## Checklist

```text
- [ ] Role, team, systems, buddy, starter tasks, 90-day project gathered
- [ ] Access and equipment requested before day one
- [ ] Starter task scoped with a reviewer
- [ ] Week one has daily goals; first change merged by day 5
- [ ] 30/60/90 outcomes are checkable and grow in scope
- [ ] People-to-meet table with reasons
- [ ] Weekly 1:1 + milestone reviews scheduled
- [ ] Unknowns left as <TODO>; nothing invented
- [ ] One to two pages; links instead of copied docs
```

## Anti-Patterns (What NOT to do)

* **A reading list as week one** — people learn by doing; give them a real task.
* **Vague outcomes** ("understand the codebase") — can't be checked; use "shipped X", "can deploy Y".
* **Access requested on day one** — it takes days; request it before.
* **No buddy** — new hires hesitate to interrupt the manager with small questions.
* **Invented names or projects** — the manager must fill in the real ones.
* **Same plan for every level** — a senior hire's 90 days should include leading, not just shipping.

## Examples

### Example 1: a backend engineer

**User:** "New backend engineer (mid-level) starts Dec 1 on Payments. Buddy is Priya. Starter
task: add a missing index for slow refund lookups. 90-day project: own the webhook retry service.
We do on-call."

**Expected output:**

```markdown
# Onboarding: <name>, Backend Engineer II — Payments — starts Dec 1
**Manager:** <you> · **Buddy:** Priya

## Before day one
- Laptop shipped; GitHub, AWS (read-only), Datadog, PagerDuty, Slack invites sent by Nov 24
- Invites: standup, sprint planning, weekly 1:1, Payments demo
- Starter task ticket ready: index for refund lookups (context, query, reviewer: Priya)

## Week one
| Day | Goals |
|---|---|
| 1 | Setup, team intro, lunch with Priya |
| 2 | Local environment running; walk through a checkout request with Priya |
| 3 | Start the refund index: write the migration, run the slow query before/after |
| 4 | PR for the index reviewed (see db-migration-safety for the concurrent build) |
| 5 | Index merged and deployed with Priya; demo it at the team demo |

## 30 / 60 / 90 days
- **30:** 3+ PRs merged; has deployed alone; shadowed one on-call week; met everyone below.
- **60:** shipped a medium change to webhooks end to end (e.g. retry backoff config); reviews
  team PRs; on-call secondary.
- **90:** owns the webhook retry service: on-call primary for it, wrote its runbook, and
  presented a plan for its next quarter.

## People to meet
| Who | Why | When |
|---|---|---|
| Priya (buddy) | Day-to-day questions | Daily, week 1 |
| <Finance partner> | Refund and reconciliation needs | Week 2 |
| <Support lead> | Top payment tickets | Week 2 |
| <Platform on-call lead> | Deploys and incidents | Week 3 |

## Check-ins
Weekly 1:1 (<TODO: day>). 30/60/90 reviews against the outcomes above, both directions.
First assignment for the onboarding doc itself: fix one thing that was wrong or missing.
```

### Example 2: resetting a struggling start

**User:** "My new analyst is 5 weeks in and hasn't delivered anything. What do I do?"

**Expected output:**

```text
Reset with a smaller, concrete target rather than more reading:
1. In your next 1:1, ask what's blocking: access? unclear data? fear of asking? Often it's an
   unscoped first project.
2. Pick one real question with a known answer path (e.g. "weekly active accounts by plan for the
   last quarter") and a reviewer, due in 3–4 days.
3. Pair them with a buddy for 30 min daily that week.
4. Set the next two milestones in writing (week 7 and week 9) and review them together.
If the plan never had week-by-week outcomes, that's on the plan, not only the person.
```

## Quick Reference

| Phase | Goal |
|---|---|
| Before day one | Access, equipment, invites, starter task ready |
| Week one | Environment running; first change merged by Friday |
| 30 days | Several small contributions; can deploy; met key people |
| 60 days | Medium change end to end; reviewing others |
| 90 days | Owns an area or leads a project |
| Throughout | Buddy, weekly 1:1, milestone reviews |
