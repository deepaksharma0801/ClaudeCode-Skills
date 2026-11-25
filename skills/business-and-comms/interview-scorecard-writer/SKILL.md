---
name: interview-scorecard-writer
description: Builds a structured interview kit with competencies, questions, and behavioral rating anchors, and writes evidence-based interview feedback. Use when preparing interviews or writing up a candidate.
---

# Detailed Instructions

Decide what "good" looks like **before** meeting anyone: a few competencies tied to the job,
questions that draw out evidence for each, and rating anchors that describe observable
behavior at each level. Then write feedback as evidence ("they said / did X") mapped to those
anchors, not impressions. Structured interviews predict job performance better than unstructured
ones and reduce bias, because every candidate is measured against the same bar.

## When to Use

- "Create interview questions / a scorecard for a <role>"
- Designing an interview loop: who assesses what
- "Write up my interview feedback for this candidate" from notes
- Reviewing feedback that's vague or biased before a debrief

**Don't use when:** writing the job posting itself (use `job-description-writer`), or making the
final hiring decision for the user (Claude can structure the evidence; the decision belongs to
the hiring team).

## Overview

Unstructured interviews drift into chat, every interviewer asks about their favorite topic, and
feedback reads "great culture fit, strong hire" with no evidence. This skill turns the role into
3–5 competencies, assigns them across the loop so nothing is assessed twice and nothing is
missed, writes questions with follow-up probes and 1–4 rating anchors, and turns raw notes into
feedback that cites evidence per competency and ends with a clear recommendation.

## Workflow Rules

### Building the kit

1. **Competencies from the job:** 3–5, drawn from what the person will actually do (the job
   description's outcomes), e.g. "Designs reliable backend systems", "Debugs production
   issues", "Communicates trade-offs in writing". Avoid vague ones like "culture fit"; use
   observable values like "Gives and takes feedback constructively".
2. **Assign competencies to interviews** so each is assessed by at least one, ideally two, and
   no interview covers more than 2–3.
3. **Questions per competency:** 1 main question + 2–3 probes. Use behavioral ("Tell me about a
   time you…") or work-sample ("Here's a failing service log; walk me through it"). Same core
   questions for every candidate.
4. **Rating anchors (1–4)** describing behavior, not adjectives:
   1 = no evidence or concerning, 2 = partial, 3 = meets the bar for the level, 4 = exceeds.
   Write what a 2 and a 3 look like specifically — that's where decisions happen.
5. **Remove non-job-related and illegal topics:** age, family plans, religion, nationality,
   health, marital status. Keep any question you'd struggle to justify as job-related off the list.

### Writing feedback

6. Write feedback **before** the debrief and before reading other interviewers' feedback, so
   their opinions don't anchor yours.
7. For each competency: the rating, then 2–3 pieces of **evidence** (what they said or did,
   quoted or paraphrased), then any concern with its evidence.
8. Leave out non-evidence: appearance, accent, school prestige, "reminds me of", "seems young",
   personal life. Replace "not a culture fit" with the specific behavior observed.
9. End with an overall recommendation (strong no / no / yes / strong yes) and the one thing
   that most drove it. If evidence for a competency is missing, say so instead of guessing.

## Output shape

```markdown
# Interview: <name> (<length>) — <role, level>
Competencies assessed: <1–3>
Exercise / main questions   same for every candidate
Probes                      2–3 per question
Anchors                     table per competency: 1 | 2 | 3 | 4 (observable behavior)

Feedback (per candidate)
<Competency> — <rating>     evidence bullets, concerns with evidence
Recommendation              strong no / no / yes / strong yes + main reason
```

## Checklist

```text
- [ ] 3–5 competencies tied to the job's real work
- [ ] Each competency covered by ≥ 1 interview; ≤ 3 per interview
- [ ] Same core questions for all candidates; probes listed
- [ ] Behavioral anchors for 1–4, especially 2 vs 3
- [ ] No non-job-related or illegal topics
- [ ] Feedback written independently, before debrief
- [ ] Each rating backed by quoted/paraphrased evidence
- [ ] Bias language removed; missing evidence stated
- [ ] Recommendation + the main reason
```

## Anti-Patterns (What NOT to do)

* **"Culture fit" as a competency** — it hides bias; name the behavior you need.
* **Different questions for each candidate** — answers can't be compared.
* **Adjective anchors** ("good", "excellent") — two interviewers will read them differently.
* **Feedback that's all impressions** ("smart", "great energy") — no evidence, no decision.
* **Reading other feedback first** — anchors your rating to theirs.
* **Making the hire/no-hire call for the team** — structure the evidence; the team decides.

## Examples

### Example 1: a scorecard for one interview

**User:** "Make a scorecard for the debugging interview for a mid-level backend engineer."

**Expected output:**

```markdown
# Interview: Production debugging (60 min) — Backend Engineer II

**Competencies assessed:** Debugs production issues methodically · Communicates while working

**Exercise:** The candidate gets a dashboard screenshot (p95 latency up 6× since 14:00), a
50-line log excerpt, and a recent deploy list. "Checkout is slow. Walk me through what you'd do."

**Probes**
- "What would you check first, and why that?"
- "The DB CPU is normal. What does that rule out?"
- "You've found it. What would you do in the next 10 minutes vs. the next week?"

**Anchors — Debugs methodically**
| 1 | 2 | 3 | 4 |
|---|---|---|---|
| Guesses fixes without looking at data; restarts things | Looks at data but jumps between ideas; needs hints to connect the deploy timing | Forms a hypothesis from the timing and logs, tests it, narrows to the deploy and the slow query | Also proposes mitigation first (rollback), and a prevention (alert, test) |

**Anchors — Communicates while working**
| 1 | 2 | 3 | 4 |
|---|---|---|---|
| Works silently; can't explain reasoning | Explains when asked | Narrates hypotheses and why they're dropped | Summarizes status crisply, as for an incident channel |
```

### Example 2: rewriting feedback

**User:** "Clean up my feedback: 'Really smart guy, great energy, went to MIT. Bit slow on the
debugging but I think he'd fit in well with the team. Hire.'"

**Expected output:**

```markdown
**Debugs methodically — 2 (partial)**
- Evidence: <what did he check first? did he use the deploy timing?> — the notes don't say.
- Concern: needed a hint to look at the deploy list (paraphrasing "bit slow" — please confirm
  what happened).

**Communicates while working — <rating?>**
- Evidence needed: did he explain his reasoning unprompted?

**Recommendation:** <yes/no> — main reason: <evidence-based>.

Removed: "smart", "great energy" (impressions, not evidence), "went to MIT" (not assessed in
this interview), "fit in well" (replace with a specific behavior you observed). With a 2 on the
core competency, "Hire" needs evidence from your notes that outweighs it — add the specifics
before the debrief.
```

## Quick Reference

| Do | Instead of |
|---|---|
| 3–5 job-based competencies | "Culture fit", "smart" |
| Same core questions for all | Free-form chat |
| Behavioral anchors 1–4 | "Good / excellent" |
| Evidence per rating | Impressions |
| Write before the debrief | Reading others first |
| State missing evidence | Guessing a rating |
