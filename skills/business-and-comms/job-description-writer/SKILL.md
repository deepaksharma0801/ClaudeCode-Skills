---
name: job-description-writer
description: Writes an inclusive, specific job description with the real work, must-have vs. nice-to-have skills, pay range, and process. Use when drafting or reviewing a job posting or role description.
---

# Detailed Instructions

Describe the job, not an imaginary perfect candidate: what this person will actually do in their
first year, the few skills they truly need on day one, the pay, and how hiring works. Specific,
honest postings attract people who fit and let others rule themselves out. Inflated requirement
lists and vague hype push away strong candidates, especially those who apply only when they meet
every bullet.

## When to Use

- "Write a job description / posting for a senior backend engineer"
- Turning a hiring manager's notes into a posting
- Reviewing a draft for vague, biased, or inflated language
- Updating an old posting for a changed role

**Don't use when:** writing interview questions or scorecards (different skill), or an internal
leveling document (that describes all levels, not one opening).

## Overview

Most job descriptions are a wish list of 15 requirements, "rockstar" language, and no pay or
process. This skill gets the facts from the hiring manager, writes a posting in a standard shape
that leads with the work and the impact, keeps must-haves to the few that are truly needed, states
the pay range and location policy, and checks the language for bias and jargon before handing it
over.

## Workflow Rules

1. **Gather facts** (ask for whatever's missing, in one round): team and what it owns, what this
   person will do in the first 3, 6, 12 months, level, reporting line, location/remote policy and
   time zones, pay range (and whether equity/bonus applies), the tech or tools actually used, the
   hiring steps, and anything unusual (on-call, travel, clearance). Never invent pay, benefits, or
   facts about the company.
2. **Lead with the work:** a 2–3 sentence opening on the problem the team solves and why the role
   matters. No "we're a fast-paced, dynamic team".
3. **What you'll do:** 4–6 concrete outcomes ("Own the billing service's migration to event-driven
   invoicing"), not duties ("Write code").
4. **Must-haves: 3–5, all truly required on day one.** Phrase them as abilities, not credentials
   ("Have built and operated a production web service" rather than "BS in CS + 5 years").
   Years of experience only if the hiring manager insists, as a range.
5. **Nice-to-haves: ≤ 4**, labeled clearly, plus a line inviting applicants who don't match every
   item.
6. **Pay and logistics:** the salary range (required by law in many places — e.g. Colorado,
   California, New York, Washington, and the EU pay transparency directive), location policy, visa
   sponsorship yes/no, and benefits the user gave.
7. **Hiring process:** the steps and rough timeline, and an accommodation contact.
8. **Language check:** remove gender-coded and exclusionary words (rockstar, ninja, dominate,
   aggressive, "digital native", "young team"), unexplained internal jargon, and requirements
   that aren't job-related (degree, a driving licence for a desk job). Use "you". Aim for
   400–700 words.

## Output shape

```markdown
# <Title> — <Team>
<2–3 sentences: the problem, why this role matters>
## What you'll do        4–6 outcomes
## What you'll need      3–5 must-haves
## Nice to have          ≤ 4, labeled; "apply even if…" line
## Pay and logistics     range, location, sponsorship, benefits given
## How we hire           steps, timeline, accommodations
```

## Checklist

```text
- [ ] Facts from the hiring manager; nothing invented (pay, benefits, perks)
- [ ] Opens with the work and its impact
- [ ] 4–6 outcome-based responsibilities
- [ ] 3–5 must-haves, all day-one, phrased as abilities
- [ ] ≤ 4 nice-to-haves, clearly labeled; "apply even if" line
- [ ] Pay range, location, sponsorship stated
- [ ] Hiring steps, timeline, accommodation contact
- [ ] Coded/exclusionary language and needless degree requirements removed
- [ ] 400–700 words
```

## Anti-Patterns (What NOT to do)

* **A 15-bullet requirements list** — it describes nobody and deters qualified people.
* **"Competitive salary"** — post the range; it's often legally required and always respected.
* **Hype words** (rockstar, ninja, crush it, work hard play hard) — they signal culture problems and skew the applicant pool.
* **Listing every technology in the stack** — name what the person will use weekly.
* **Degree requirements by default** — require one only if the job truly needs it.
* **Invented perks or numbers** — leave a placeholder for the user to fill.

## Examples

### Example 1: from hiring-manager notes

**User:** "Senior backend engineer, Payments team. Python/Django, Postgres, some Kafka. They'll lead
moving invoicing to events, and be on-call one week in six. Remote in US time zones, $165k–$195k
plus equity. Process: recruiter call, technical chat, take-home (2h max), team interviews."

**Expected output:**

```markdown
# Senior Backend Engineer — Payments

Payments moves every dollar our customers earn. We're changing how invoicing works, from nightly
batch jobs to events in real time, so customers see accurate bills the moment usage happens. You'll
lead that change.

## What you'll do
- Lead the migration of invoicing from batch jobs to an event-driven design on Kafka.
- Design and ship Django services and Postgres schemas that handle money correctly — idempotent,
  auditable, and easy to reconcile.
- Take part in on-call one week in six, and make incidents rarer each quarter.
- Review code and mentor two mid-level engineers on the team.
- Work with Finance and Support to turn billing problems into product fixes.

## What you'll need
- Experience building and operating production backend services in Python.
- Strong relational database skills: schema design, migrations, and query performance in Postgres
  or similar.
- You've led a technical project across several engineers from design to rollout.
- Clear written communication — we work remote-first and decide in docs.

## Nice to have
- Kafka or another event-streaming system in production.
- Payments, billing, or ledger experience.
- Django specifically (strong Python + another framework is fine).

Don't meet every point? Apply anyway — we care most about the "What you'll need" list.

## Pay and logistics
- Salary: $165,000–$195,000, plus equity.
- Remote within the US; overlap with US time zones.
- On-call: one week in six, with <TODO: confirm on-call compensation>.
- Visa sponsorship: <TODO: confirm>.

## How we hire
1. 30-minute recruiter call
2. Technical conversation with an engineer (60 min)
3. Take-home exercise, 2 hours max
4. Team interviews: system design, code review, and working together
We aim to finish within 3 weeks <TODO: confirm>. Need an accommodation? Email <TODO: contact>.
```

### Example 2: reviewing a biased draft

**User:** "Review this: 'Looking for a coding ninja to dominate our backend. Must have CS degree,
10+ years Java, Kotlin, Go, Rust, AWS, GCP, Kubernetes, Terraform. Young, energetic team.
Competitive pay.'"

**Expected output:**

```text
Five problems:
1. "ninja", "dominate" — gender-coded hype; describe the work instead.
2. "Young, energetic team" — signals age bias (a legal risk under US age-discrimination law).
3. CS degree + 10+ years — likely not job-related; ask what someone needs to do on day one.
4. Eight technologies as requirements — which ones are used weekly? Keep 2–3 as must-haves,
   move others to nice-to-have.
5. "Competitive pay" — give the range (required in several US states and under the EU pay transparency directive).

Send me what the person will work on in their first 6 months, the range, and the location, and
I'll rewrite it.
```

## Quick Reference

| Instead of | Write |
|---|---|
| "Rockstar / ninja" | The job title |
| "Fast-paced, dynamic" | The problem the team solves |
| "Responsible for writing code" | "Lead the migration of X to Y" |
| "BS in CS + 7 years" | "Have built and operated a production service" |
| 15 requirements | 3–5 must-haves + ≤ 4 nice-to-haves |
| "Competitive salary" | "$165,000–$195,000 + equity" |
| No process | Steps, timeline, accommodation contact |
