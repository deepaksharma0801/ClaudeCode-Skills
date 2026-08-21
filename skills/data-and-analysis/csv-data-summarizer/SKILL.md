---
name: csv-data-summarizer
description: Profiles a CSV or TSV file for column types, distributions, missing data, and correlations. Use when a user shares a tabular data file or asks what is in their data.
dependencies: python>=3.8, pandas>=1.5.0
---

# Detailed Instructions

Profile the file first, interpret second. Never describe a column you have not measured.

## Overview

The user has tabular data and does not yet know its shape, quality, or interesting relationships.
This skill produces a consistent profile — structure, quality, distributions, correlations — in a
single pass, so the user does not have to ask for each piece separately.

## Workflow Rules

1. Load the file with `pandas.read_csv`, inferring the separator (`sep=None, engine="python"`) so
   TSV and semicolon-delimited files work without asking the user.
2. Report shape: row count and column count.
3. For every column, report the inferred dtype, non-null count, and unique count.
4. Flag data-quality issues: columns over 20% null, constant columns, exact duplicate rows, and
   numeric columns stored as strings.
5. For numeric columns, report min / median / max / mean / std.
6. For categorical columns with 20 or fewer distinct values, report the value counts. Above 20,
   report only the top 5 and the cardinality.
7. Compute the Pearson correlation matrix for numeric columns and surface only pairs with
   `|r| >= 0.5`, strongest first.
8. Close with a short "What stands out" section: at most 5 bullets, each tied to a number you
   actually computed.

## Anti-Patterns (What NOT to do)

* Do not ask the user which columns to analyze. Profile all of them.
* Do not print the full dataframe or a full correlation matrix. Summaries only.
* Do not infer causation from correlation, or recommend a model, unless the user asks.
* Do not silently drop rows. If you exclude anything, say how many and why.
* Do not guess at the meaning of a cryptic column name. Report the name and its statistics as-is.

## Examples

**User:** "Here's my sales export, what am I looking at?" *(attaches `sales_q3.csv`)*

**Expected output:**

```text
## Structure
4,182 rows x 9 columns

| column      | dtype   | non-null | unique |
|-------------|---------|----------|--------|
| order_id    | object  | 4182     | 4182   |
| order_date  | object  | 4182     | 92     |
| region      | object  | 4182     | 4      |
| units       | int64   | 4182     | 37     |
| unit_price  | float64 | 4021     | 214    |
| discount    | float64 | 1104     | 12     |
| revenue     | float64 | 4021     | 3877   |

## Data quality
- `discount`: 73.6% null (3,078 of 4,182) — likely "no discount applied" rather than missing
- `order_date` is stored as text, not datetime
- 14 exact duplicate rows

## Distributions
- units: min 1, median 3, max 48, mean 4.2, std 3.8
- revenue: min 12.50, median 184.00, max 9,240.00, mean 291.40, std 402.10
- region: North 1,502 / South 1,188 / East 874 / West 618

## Correlations (|r| >= 0.5)
- units ~ revenue: r = 0.81
- unit_price ~ revenue: r = 0.57

## What stands out
- Revenue is driven more by unit count (r = 0.81) than by price (r = 0.57).
- 161 rows have units but no unit_price, so their revenue is also missing.
- West is the smallest region at 14.8% of orders, less than half of North.
- Dates span 92 distinct days; parse `order_date` before any trend analysis.
```
