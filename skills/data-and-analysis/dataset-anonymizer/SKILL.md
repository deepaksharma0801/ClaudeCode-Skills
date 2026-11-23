---
name: dataset-anonymizer
description: De-identifies a dataset before sharing by hashing IDs, generalizing fields, redacting free text, and checking re-identification risk. Use before sharing data with vendors or LLMs.
compatibility: Bundled script requires Python 3.8+ (standard library only).
---

# Detailed Instructions

Decide what each column is for the recipient before transforming it, and treat any column you did
not explicitly handle as a leak. Removing names is not anonymization; combinations like ZIP +
birth date + gender re-identify people.

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

## Anti-Patterns (What NOT to do)

* Do not treat dropping the name and email columns as anonymization.
* Do not use unsalted hashes of emails, phone numbers, or IDs; they can be reversed by guessing.
* Do not ship the HMAC key, the rules file with secrets, or the original file alongside the output.
* Do not leave free-text columns untouched; they routinely contain names, emails, and card numbers.
* Do not declare a dataset "GDPR/HIPAA compliant"; describe the transformations and residual risk.
* Do not generalize so aggressively that the data no longer answers the recipient's question.

## Examples

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
