---
name: csv-data-summarizer
description: Profiles a CSV or TSV file for column types, missing data, distributions, quality problems, and correlations. Use when a user shares a tabular data file or asks what is in their data.
compatibility: Bundled profiler requires Python 3.8+ (standard library only). pandas is optional for follow-up analysis.
---

# Detailed Instructions

Profile the whole file first, interpret second. Never describe a column you haven't measured, and
tie every observation in the summary to a number you computed. The user usually doesn't know
what to ask yet — a consistent profile of structure, quality, distributions, and relationships
tells them where the interesting questions are and where the data can't be trusted.

## When to Use

- "What's in this file?", "summarize this CSV", "explore this dataset"
- A spreadsheet export (CSV/TSV) shared before analysis
- Checking data quality before a report, model, or import

**Don't use when:** the user asks a specific question about the data (answer it directly — profile
only the columns it needs), the file is Excel (convert with the xlsx tooling first or read the
sheet), or the data must be de-identified before anyone looks at it (use `dataset-anonymizer`).

## Overview

Without a procedure, models eyeball the first rows, guess column meanings from names, and miss
what matters: a revenue column stored as text with dollar signs, a 60%-empty field, duplicate
rows, a date column that's really a string. This skill runs `scripts/profile_csv.py` for the full
mechanical profile (no dependencies), then reads it like an analyst — what's broken, what's
skewed, what's related — and writes a short, numbers-backed summary.

## Workflow Rules

### 1. Profile

1. **Run the profiler on the whole file:** `python3 scripts/profile_csv.py data.csv`
   (`--max-rows 500000` for very large files, saying so in the summary). It sniffs the delimiter,
   infers types, counts missing values (including "NA", "null", "-"), uniques, numeric stats, top
   values, duplicates, ragged rows, and correlations with |r| ≥ 0.5.
2. **If the file is too large or the profiler can't parse it**, fall back to pandas with
   `pd.read_csv(path, sep=None, engine="python")`, and report the same sections.

### 2. Read it critically

3. **Structure:** rows × columns; whether a column looks like a unique ID; whether the grain is
   clear (one row per order? per order line?).
4. **Quality first**, because it changes how everything else is read:
   - columns > 20% missing — and whether "missing" likely means "zero/none" (e.g. discount)
   - numbers or dates stored as text (currency symbols, commas, `%`, mixed formats)
   - constant columns, exact duplicate rows, ragged rows
   - IDs that aren't unique when they should be
5. **Distributions:** for numeric columns, min / median / max / mean / std — note skew when mean
   and median differ a lot, and impossible values (negative quantities, future dates). For
   categorical columns, value counts (all of them if ≤ 20 values, otherwise top 5 + cardinality).
6. **Relationships:** only pairs with |r| ≥ 0.5, strongest first, with n. Correlation between
   columns where one is computed from the other (revenue = units × price) is expected — say so
   rather than presenting it as a finding.

### 3. Summarize (this shape)

```text
## Structure        rows x columns, delimiter, grain if clear
## Column table     column | type | non-null | missing | unique
## Data quality     each issue with counts, and what it likely means
## Distributions    numeric stats; categorical counts
## Correlations     |r| >= 0.5, with n, flagged if mechanical
## What stands out  at most 5 bullets, each tied to a computed number
```

7. **Offer next steps** the data supports (parse dates, deduplicate, a specific breakdown) — don't
   run them unasked.

## Checklist

```text
- [ ] Ran scripts/profile_csv.py on the whole file (or said it was sampled)
- [ ] Grain and ID columns identified
- [ ] Quality issues listed with counts
- [ ] Numbers/dates stored as text flagged
- [ ] Skew and impossible values noted
- [ ] Correlations filtered to |r| >= 0.5; mechanical ones labeled
- [ ] "What stands out" ≤ 5 bullets, each with a number
```

## Anti-Patterns (What NOT to do)

* **Asking which columns to analyze** — profile all of them; that's the point.
* **Printing the dataframe or a full correlation matrix** — summaries only.
* **Inferring causation from correlation, or recommending a model unprompted** — describe, don't prescribe.
* **Silently dropping rows** — if anything is excluded, say how many and why.
* **Guessing what a cryptic column means** — report the name and its numbers as they are.
* **Describing from the first 10 rows** — the issues are usually further down.

## Examples

### Example 1: a sales export

**User:** "Here's my sales export, what am I looking at?" *(attaches `sales_q3.csv`)*

**Expected output:**

```text
## Structure
405 rows x 9 columns (comma-separated). One row per order (order_id), but see duplicates.

| column      | type                | non-null | missing | unique |
|-------------|---------------------|----------|---------|--------|
| order_id    | text                | 405      | 0       | 400    |
| order_date  | date/time (as text) | 405      | 0       | 60     |
| region      | text                | 405      | 0       | 4      |
| units       | int                 | 405      | 0       | 12     |
| unit_price  | float               | 379      | 26      | 360    |
| discount    | float               | 152      | 253     | 2      |
| revenue     | float               | 379      | 26      | 370    |
| price_text  | text                | 405      | 0       | 361    |
| source      | text                | 405      | 0       | 1      |

## Data quality
- 5 exact duplicate rows (order_id has 400 unique values in 405 rows) — likely a double export.
- discount: 62.5% missing (253 of 405) — probably "no discount" rather than unknown.
- unit_price and revenue missing on the same 26 rows.
- price_text: numbers stored as text with "$"; 26 values are just "$" (the missing prices).
- order_date is text; parse it before any trend analysis.
- source is constant ("web") — carries no information.

## Distributions
- units: min 1, median 6, max 12, mean 6.35
- revenue: min 5.86, median 199.90, max 900.12, mean 263.11 (mean > median: right-skewed)
- region: North 166 / West 82 / South 81 / East 76

## Correlations (|r| >= 0.5)
- unit_price ~ revenue: r = 0.67 (n = 379)  — expected: revenue = units × unit_price
- units ~ revenue: r = 0.66 (n = 379)       — expected, same reason

## What stands out
- Remove 5 duplicate orders before totals; they overstate revenue.
- 26 orders (6.4%) have no price and so no revenue.
- North has about twice the orders of any other region (166 vs 76–82).
- Revenue is right-skewed; report medians alongside means.

Next: deduplicate and parse order_date, then revenue by week and region?
```

### Example 2: a messy European export

**User:** "This file looks broken when I open it." *(semicolon-separated, decimal commas, `#N/A` values)*

**Expected output:**

```text
## Structure
12,480 rows x 14 columns (semicolon-separated — Excel in a European locale).

## Data quality
- amount, vat, total: numbers stored as text — they use decimal commas ("1.234,56"). Convert with
  pd.read_csv(path, sep=";", decimal=",", thousands=".") before any math.
- customer_segment: 41.2% "#N/A" (5,142 rows) — an Excel lookup that failed, not true blanks.
- 37 rows have 13 fields instead of 14 (a free-text "notes" field with an unquoted semicolon).

Nothing else can be trusted until these are fixed; want me to reload it with the right
separator and decimal settings and re-profile?
```

## Quick Reference

| Finding | Usual meaning | Next step |
|---|---|---|
| Numbers as text with `$`, `,`, `%` | Export formatting | Parse with thousands/decimal settings |
| > 20% missing | Optional field or broken join | Decide: zero, unknown, or exclude |
| Duplicate rows | Double export or join fan-out | Deduplicate before totals |
| Mean ≫ median | Right skew | Report medians |
| High r between derived columns | Mechanical relationship | Label it; don't call it a finding |
| Ragged rows | Unquoted delimiters in text | Fix quoting; re-export |
