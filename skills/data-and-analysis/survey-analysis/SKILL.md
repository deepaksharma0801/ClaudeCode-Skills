---
name: survey-analysis
description: Analyzes survey results with response rates, margins of error, Likert distributions, segment comparisons, and coded open-ended answers. Use for customer, employee, NPS, or user research surveys.
---

# Detailed Instructions

Report what the respondents said, with its uncertainty, and be explicit about who did not respond.
A survey describes the people who answered it, not automatically everyone you sent it to.

## Overview

Survey readouts commonly overstate precision ("satisfaction rose from 71% to 74%"), average Likert
scales as if they were measurements, slice small groups until something looks significant, and
skip the open-ended answers that explain the numbers. This skill reports response rate and bias,
distributions with margins of error, careful segment comparisons, and a coded summary of free text.

## Workflow Rules

1. **Context:** who was invited, how many responded, how they were sampled, and the exact question
   wording and scale. Compute the **response rate** and compare respondents with the invited
   population on known attributes (plan, tenure, region) to spot non-response bias.
2. **Clean:** remove test and duplicate responses, speeders (completion far faster than median),
   and straight-liners on grids; report how many were removed.
3. **Closed questions:**
   - Report the full distribution, plus top-2-box (e.g. % "Agree" + "Strongly agree").
   - Give a 95% margin of error for proportions: ±1.96 × √(p(1−p)/n).
   - Means of Likert items may be shown as a secondary summary only, never alone.
   - NPS = % promoters (9–10) − % detractors (0–6); with n < 200, report its interval or say it is noisy.
4. **Comparisons** (segments, or this survey vs the last one): only for groups with enough
   responses (rule of thumb n ≥ 30 per group); test proportions (two-proportion z-test or
   chi-square) and say "no detectable difference" when the interval includes zero. Limit the number
   of comparisons, and correct for many.
5. **Open-ended answers:** read a sample, build a codebook of 5–10 themes with definitions, code
   every answer (multiple codes allowed), count themes, and quote 1–2 short representative answers
   per theme (anonymized).
6. **Report:** headline findings tied to numbers with margins of error, the top themes from free
   text, segment differences that are real, and caveats (response rate, bias, wording).

## Anti-Patterns (What NOT to do)

* Do not report percentages without n, or changes smaller than the margin of error as real.
* Do not present a Likert mean alone as the result.
* Do not slice into many small segments and highlight whichever looks different.
* Do not generalize to the whole customer base when the response rate is low and respondents differ.
* Do not quote open-ended answers that identify the respondent.
* Do not ignore the open-ended answers; they explain the numbers.

## Examples

**User:** "Here are 412 responses to our customer satisfaction survey (sent to 3,800 customers). Last quarter, 71% said satisfied (n=389). Did we improve?" *(survey.csv)*

**Expected output:**

```text
## Response
412 of 3,800 invited (10.8%). Removed 9 speeders (< 40 s vs 3 min median) → n = 403.
Respondents skew to annual-plan customers: 58% of respondents vs 41% of invitees. Annual
customers are usually more satisfied, so overall satisfaction is likely overstated a little.

## Satisfaction ("Overall, how satisfied are you?" 5-point)
| Very dissatisfied | Dissatisfied | Neutral | Satisfied | Very satisfied |
| 4%                | 9%           | 13%     | 46%       | 28%            |
Satisfied (top-2-box): 74% ± 4.3 points (n = 403)

## vs last quarter
71% (n = 389) → 74% (n = 403): +3 points, 95% CI −3.2 to +9.2; p = 0.34.
No detectable change — the difference is within sampling noise.

## Segments (n ≥ 30)
- Monthly-plan: 66% ± 7.2 (n = 169) vs annual: 80% ± 5.1 (n = 234) — real gap of 14 points (95% CI 5 to 23; p = 0.002).

## Open-ended: "What should we improve?" (291 answers, coded)
| Theme                         | Share |
|-------------------------------|-------|
| Slow support responses        | 31%   |
| Missing integrations          | 22%   |
| Pricing / value               | 18%   |
| Mobile app bugs               | 12%   |
"I waited three days for a reply about a billing error." · "We need a HubSpot sync."

## Caveats
10.8% response rate and an annual-plan skew. Weight by plan type before quoting a company-wide number.
```
