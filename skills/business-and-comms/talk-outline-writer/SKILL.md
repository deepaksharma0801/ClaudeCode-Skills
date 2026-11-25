---
name: talk-outline-writer
description: Outlines a talk, demo, or presentation around one message, with a hook, three supporting points, timed sections, and a slide-by-slide plan. Use when preparing a conference talk, tech talk, or demo.
---

# Detailed Instructions

Decide the **one sentence the audience should remember**, then build everything to support it:
a hook that shows why it matters, at most three points that prove it, a concrete example or demo,
and an ending that restates it with what to do next. Timing is part of the design. A talk with
five messages leaves the audience with none, and a talk that runs over gets its conclusion cut.

## When to Use

- "Help me outline a talk on X" (conference, meetup, internal tech talk, lightning talk)
- Turning a blog post, design doc, or project into a presentation
- Planning a product or technical demo
- Writing a talk proposal (CFP) abstract

**Don't use when:** writing the article itself (use `technical-blog-post`), or explaining an
incident or decision to leadership (use `explain-for-stakeholders` or `decision-memo`).

## Overview

Talk drafts usually start with the speaker's history ("first, some background about our
team…"), cover everything they know, and end with "questions?". This skill fixes the
audience and length, writes the one-sentence message, picks three points with evidence, plans a
hook and an ending, allocates minutes per section, and produces a slide-by-slide outline with
speaker notes — plus a demo plan with a fallback if there's a demo.

## Workflow Rules

1. **Fix the constraints:** audience (what they already know, why they came), length, format
   (talk, lightning, workshop, demo), and the venue's slide/recording rules.
2. **One message** in one sentence: "Partial indexes cut our slowest queries 18× with no
   application changes." If you can't write it, the talk isn't ready to outline.
3. **Three points (max)** that support the message, each with evidence: a number, a story, a
   code sample, or a demo.
4. **Hook (first 60 seconds):** a problem the audience recognizes, a surprising number, or a
   short story — not an agenda or a bio. One line of intro is enough.
5. **Ending:** restate the message, give 1–3 things to do next (try X, read Y, link to repo), and
   stop on time. Put Q&A after the ending, not as the ending.
6. **Time budget:** roughly 10% hook, 75% points (split evenly), 15% ending, and leave ~10% slack
   in rehearsal. About 1 slide per minute is a sane average; fewer for story-heavy talks.
7. **Slides:** one idea per slide, a headline that states the point ("p95 dropped from 2.1 s to
   120 ms"), large code fonts (≤ 15 lines), and no paragraphs. Detail goes in speaker notes.
8. **Demos:** script every step, use pre-loaded data, have a recorded video or screenshots as a
   fallback, and know exactly what to cut if time runs short.
9. **CFP abstract (if asked):** the problem, the message, what attendees will take away, in
   ~100–150 words.

## Output shape

```markdown
# <Title stating the payoff>
Audience · Length · Format
Message: <one sentence>
## Timed outline     section | minutes | content
## Slides            # | headline | visual | speaker note
## Demo plan         steps, data, fallback (if any)
## Takeaways         1–3 next actions for the audience
```

## Checklist

```text
- [ ] Audience, length, format known
- [ ] One-sentence message written
- [ ] ≤ 3 points, each with evidence
- [ ] Hook in the first minute (no agenda/bio opening)
- [ ] Ending restates message + next actions, before Q&A
- [ ] Minutes allocated; ~10% slack
- [ ] Slides: one idea, headline = point, readable code
- [ ] Demo scripted with a fallback
```

## Anti-Patterns (What NOT to do)

* **Opening with an agenda and team history** — the audience decides in the first minute whether to listen.
* **Five-plus key points** — none stick; cut to three.
* **Slides as a script** — paragraphs on slides compete with the speaker.
* **Live demos with no fallback** — Wi-Fi and auth fail on stage.
* **Ending on "Questions?"** — end on the message, then take questions.
* **Tiny code** — if the back row can't read it, it isn't there.

## Examples

### Example 1: a 25-minute meetup talk

**User:** "25-minute talk at a Postgres meetup about how we fixed slow queries with partial
indexes. Our worst query went from 2.1 s to 120 ms."

**Expected output:**

```markdown
# Index Less, Query Faster: Partial Indexes in Production
**Audience:** Postgres users, mixed experience · **Length:** 25 min + Q&A · **Format:** talk

**Message:** Partial indexes made our slowest queries about 18× faster with no application
changes — and most teams have queries that would benefit.

## Timed outline
| Section | Min | Content |
|---|---|---|
| Hook | 2 | The 2.1 s query that paged us weekly; show the EXPLAIN |
| Point 1: why full indexes didn't help | 6 | 98% of rows are `status = 'done'`; the planner's choice |
| Point 2: the partial index | 7 | `CREATE INDEX … WHERE status = 'pending'`; size 4.2 GB → 80 MB; EXPLAIN after |
| Point 3: finding candidates in your DB | 6 | Query `pg_stat_statements` + column selectivity; pitfalls (predicate must match) |
| Ending | 2 | Restate; 3 steps to try Monday; repo link |
| Slack | 2 | |

## Slides (excerpt)
| # | Headline | Visual | Note |
|---|---|---|---|
| 1 | "This query paged us every week" | p95 chart, 2.1 s | Tell the on-call story in 30 s |
| 4 | "98% of the index points at rows we never query" | bar: done vs pending | The core insight |
| 7 | "2.1 s → 120 ms, index 4.2 GB → 80 MB" | before/after EXPLAIN | Pause here |
| 11 | "Try it Monday" | 3 steps | Restate the message |

## Takeaways
1. Find queries filtering on a rare value (`pg_stat_statements`).
2. Check selectivity of that predicate.
3. Build a partial index `CONCURRENTLY` and compare EXPLAIN.
```

(2.1 s / 120 ms ≈ 17.5×, rounded to "about 18×".)

### Example 2: a 5-minute lightning talk

**User:** "Lightning talk, 5 minutes, about our feature flag cleanup."

**Expected output:**

```text
Five minutes = one point, one story. Message: "We deleted 90 stale feature flags in a month by
giving every flag an expiry date."
- 0:00–0:45 Hook: the bug caused by a flag nobody remembered (one slide)
- 0:45–3:30 The rule: owner + expiry on every flag, CI warns on expired ones; show the CI
  output and the count dropping (3 slides)
- 3:30–4:30 What it took: one script, one policy, one month (1 slide)
- 4:30–5:00 Ending: "Give every flag an expiry date." + link (1 slide)
Six slides total. Cut the history of how flags piled up — there's no time for it.
```

## Quick Reference

| Part | Rule |
|---|---|
| Message | One sentence, written first |
| Points | ≤ 3, each with evidence |
| Hook | Problem, number, or story in the first minute |
| Ending | Message + next steps, then Q&A |
| Time | ~10% hook · 75% points · 15% ending; keep slack |
| Slides | One idea, headline = the point, ≤ 15 lines of code |
| Demo | Scripted, pre-loaded data, recorded fallback |
