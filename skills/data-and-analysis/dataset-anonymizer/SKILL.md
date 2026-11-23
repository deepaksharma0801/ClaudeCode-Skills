---
name: dataset-anonymizer
description: De-identifies a dataset before sharing by hashing IDs, generalizing fields, redacting free text, and checking re-identification risk. Use before sharing data with vendors or LLMs.
compatibility: Bundled script requires Python 3.8+ (standard library only).
---

# Detailed Instructions

Decide what each column is for the recipient before transforming it, and treat any column you did
not explicitly handle as a leak. Removing names is not anonymization; combinations like ZIP +
birth date + gender re-identify people.
Once a file is shared it can't be recalled, so mistakes here are permanent. The script makes the
transformations repeatable and lists every untouched column, so nothing leaks by omission.

## When to Use

- Sharing data with a contractor, vendor, researcher, or another team
- Pasting data into an AI tool or a public issue
- Creating realistic test or demo data from production
- Publishing a dataset or a case study

**Don't use when:** the recipient needs to contact or identify people (then it's a data-sharing
agreement question, not anonymization), or the data is already aggregated to large groups.

## Overview

Teams share data with contractors, vendors, and AI tools by "just removing the email column".
Direct identifiers then survive in free-text notes, and quasi-identifiers (ZIP, birth date, job
title) single people out. This skill classifies every column, applies the least-destructive
transformation that still serves the recipient's purpose, runs `scripts/anonymize.py`, and checks
re-identification risk with a k-anonymity count.

## Workflow Rules

1. **Purpose first:** what will the recipient do with the data (count by region, join across
   tables, train a model)? Keep only what that needs.
2. **Classify every column:**
   - **Direct identifiers** (name, email, phone, address, government ID, account number): drop, or
     `hash` if the recipient must join or count distinct people.
   - **Quasi-identifiers** (ZIP, birth date, age, gender, job title, IP, precise timestamps):
     generalize — `zip3`, `year`, `month`, `bucket:N`, `ip24`.
   - **Free text** (notes, comments, support messages): `redact` at minimum, and spot-check
     samples; drop the column if it is not needed.
   - **Non-identifying attributes** (plan, amount, status): keep.
3. **Write `rules.json`** mapping each column to an action, and run:
   `ANONYMIZE_KEY=<secret> python3 scripts/anonymize.py in.csv out.csv --rules rules.json --report --quasi zip,age,gender`
   The report lists columns copied unchanged; every one of them must be a deliberate choice.
4. **Hashing:** `hash` is a keyed HMAC, so the same email always maps to the same token (joins
   still work). Keep `ANONYMIZE_KEY` secret and never send it with the data; anyone holding it can
   re-identify values by hashing guesses. A plain unsalted SHA-256 of an email is *not* safe.
5. **Check k-anonymity** on the quasi-identifiers: the smallest group size `k` should be at least 5
   (higher for sensitive data). If it is lower, generalize further (wider buckets, coarser dates)
   or suppress the rare rows, and re-run.
6. **Spot-check** 20 random output rows, especially redacted text, before sending.
7. **Report** what was dropped, hashed, generalized, and kept; the resulting k; and residual risks.
   Note when a legal standard applies (HIPAA Safe Harbor, GDPR) — pseudonymized data is still
   personal data under GDPR — and recommend review rather than declaring compliance.

## Checklist

```text
- [ ] Recipient's purpose written down
- [ ] Every column classified (direct, quasi, free text, attribute)
- [ ] rules.json covers every column; report shows no surprise "copied unchanged"
- [ ] ANONYMIZE_KEY set from a secret, not shared
- [ ] k-anonymity on quasi-identifiers ≥ 5 (higher for sensitive data)
- [ ] 20 random output rows spot-checked, especially free text
- [ ] Residual risks and legal context stated
```

## Red Flags

- "We dropped the name and email columns, so it's anonymous."
- "SHA-256 the emails, nobody can reverse that."
- "The notes column is probably fine."
- "Send the key along so they can join the files."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "No names means anonymous." | ZIP + birth date + gender alone identifies most people in a population. Check quasi-identifiers. |
| "Hashes are irreversible." | Unkeyed hashes of emails or phone numbers can be reversed by hashing guesses. Use a keyed HMAC and keep the key. |
| "Redaction catches everything." | Pattern redaction catches emails and numbers, not names or stories in free text. Drop or review free text. |

## Anti-Patterns (What NOT to do)

* Do not treat dropping the name and email columns as anonymization.
* Do not use unsalted hashes of emails, phone numbers, or IDs; they can be reversed by guessing.
* Do not ship the HMAC key, the rules file with secrets, or the original file alongside the output.
* Do not leave free-text columns untouched; they routinely contain names, emails, and card numbers.
* Do not declare a dataset "GDPR/HIPAA compliant"; describe the transformations and residual risk.
* Do not generalize so aggressively that the data no longer answers the recipient's question.

## Examples

### Example 1: a file for a contractor

**User:** "I need to send our customers.csv to an analytics contractor so they can study churn by region and age. Make it safe."

**Expected output:**

```text
Purpose: churn by region and age group; contractor needs to count distinct customers, not contact them.

| column      | type             | action    | why                                   |
|-------------|------------------|-----------|---------------------------------------|
| user_id     | direct (join key)| hash      | count distinct customers across files |
| name        | direct           | drop      | not needed                            |
| email       | direct           | hash      | links to events.csv by email          |
| phone       | direct           | drop      | not needed                            |
| birth_date  | quasi            | year      | age analysis needs year only          |
| zip         | quasi            | zip3      | region = first 3 digits               |
| age         | quasi            | bucket:10 | age groups                            |
| ip          | quasi            | drop      | not needed                            |
| notes       | free text        | drop      | not needed for churn                  |
| plan, churned_at, mrr | attributes | keep  | the analysis itself                   |

$ ANONYMIZE_KEY=$KEY python3 scripts/anonymize.py customers.csv customers_anon.csv \
    --rules rules.json --report --quasi zip,age,birth_date
rows: 48,211
copied unchanged: plan, churned_at, mrr
k-anonymity on (zip, age, birth_date): k = 2; 37 row(s) in groups smaller than 5

k = 2 is too low: birth year + age bucket + ZIP3 singles out a few people. Dropped birth_date
(age bucket is enough) and re-ran → k = 9; 0 rows in groups smaller than 5.

Send: customers_anon.csv only. Keep ANONYMIZE_KEY in the team password manager; do not share it.
Residual risk: mrr values are exact; a contractor who knows a specific customer's price could
spot them. Round mrr to the nearest $10 if that matters.
```

### Example 2: free text that redaction can't fix

**User:** "Just run redact on the support tickets body and send them to the vendor."

**Expected output:**

```text
Ran redact on a 200-ticket sample and read 20 outputs. It removed emails, phone numbers, and card
digits, but left:
- personal names ("Hi, this is Ana from accounting")
- health and family details ("after my surgery last week", "my husband's account")
- company names and order references in prose

Pattern-based redaction isn't enough for this column. Options, safest first:
1. Don't send body; send category, product, created_month, and resolution time instead.
2. Send bodies only after a named-entity redaction pass plus a manual review of a sample.
3. Have the vendor work in your environment so the text never leaves.
```

## Quick Reference

| Column type | Default action |
|---|---|
| Name, phone, address, government ID | `drop` |
| Email / user ID needed for joins | `hash` (keyed HMAC) |
| Birth date | `year` |
| Timestamp | `month` |
| ZIP / postcode | `zip3` |
| Age | `bucket:10` |
| IP | `ip24` or `drop` |
| Free text | `drop`, or `redact` + review |
