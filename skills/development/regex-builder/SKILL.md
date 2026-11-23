---
name: regex-builder
description: Builds a regular expression from a plain description and proves it against must-match and must-not-match cases. Use when asked for a regex, or to fix, explain, or speed up one.
compatibility: Test script requires Python 3.8+ (standard library only) and tests the Python re flavor.
---

# Detailed Instructions

No regex is delivered without test cases that were actually run. Write the cases first — the
strings that must match and the near-misses that must not — then the pattern, then show the
pass/fail table. A regex that "looks right" is the most common way to ship a validation bug,
because regexes fail on the edges: unanchored matches, greedy wildcards, and engine differences.

## When to Use

- "Write a regex for…", "validate this format", "extract X from these lines"
- A regex that matches too much, too little, or nothing
- Explaining an existing regex
- A regex that is slow or times out on some inputs

**Don't use when:** the input is structured data with a real parser — HTML/XML, JSON, CSV with
quoting, URLs, email per RFC 5322, dates, or nested brackets. Use the parser or library
(`html.parser`/BeautifulSoup, `json`, `csv`, `urllib.parse`, `email.utils`, `datetime`) and say why.

## Overview

Regexes look correct and fail quietly: a validator without `^…$` accepts `"abc94103xyz"`, a `.*`
swallows half the line, `\d` matches Arabic-Indic digits in Python 3 unless `re.ASCII` is set,
lookbehind isn't supported in Go's RE2, and nested quantifiers like `(a+)+` can hang on hostile
input. This skill pins the engine, writes cases including edge cases, builds the simplest pattern
that passes, runs it with `scripts/test_regex.py` (or the target language), explains it token by
token, and states its limits.

## Workflow Rules

### 1. Pin down the job

1. **Engine/flavor:** JavaScript, Python `re`, PCRE (PHP, grep -P), Go RE2, Java, .NET, POSIX
   (grep -E, sed -E), database (Postgres `~`, MySQL `REGEXP`). Ask once if unclear and it matters
   — lookbehind, named groups, Unicode classes, and backreferences differ.
2. **Mode:** validate a whole value (must anchor), find occurrences in text (search), or extract
   groups (capture). The same pattern behaves differently in each.

### 2. Write cases first

3. **At least 5 must-match and 5 must-not-match strings**, including:
   - the empty string, leading/trailing whitespace
   - near-misses (one character short, one too long, wrong separator)
   - realistic noise around valid values (for search mode)
   - Unicode lookalikes (full-width digits, non-breaking spaces) when input is user-provided
   - very long inputs if the pattern has repetition (for backtracking)

### 3. Build the simplest passing pattern

4. **Anchor whole-value validators** with `^…$` (or use `fullmatch` in Python, `\A…\z` in Ruby/PCRE
   to avoid `$` matching before a trailing newline).
5. **Prefer explicit classes** over `.`: `[^"]*` instead of `.*?` inside quotes; `[A-Za-z0-9_-]`
   instead of `\w` when non-ASCII letters shouldn't count.
6. **Use non-capturing groups** `(?:…)` unless you need the capture.
7. **Avoid nested quantifiers** over overlapping text (`(a+)+`, `(\w+\s?)*`) — they backtrack
   exponentially. Restructure, use possessive/atomic groups where supported, or use RE2.

### 4. Prove it

8. **Run every case:**
   `python3 scripts/test_regex.py 'PATTERN' --match ... --no-match ... [--mode search] [--flags ASCII]`
   or with a cases file `--cases cases.json`. For non-Python engines, run the equivalent in that
   language (a 5-line `node -e` or `go run`). Iterate until every case passes.
9. **Check timing** on long inputs if the pattern has repetition; the script flags slow cases and
   nested quantifiers.

### 5. Explain and hand over

10. **Token table:** each piece of the pattern and what it means.
11. **Usage snippet** in the user's language with correct escaping — raw strings in Python
    (`r"..."`), double escaping in Java/JSON strings, `/.../` literals in JavaScript.
12. **Limits:** state what it doesn't check (format vs existence, partial RFC coverage) and when
    to use a library instead.

## Checklist

```text
- [ ] Engine and mode (validate / search / extract) known
- [ ] ≥ 5 must-match and ≥ 5 must-not-match cases, incl. empty, whitespace, near-misses
- [ ] Whole-value validators anchored (or fullmatch)
- [ ] No unnecessary `.*`; non-capturing groups where possible
- [ ] No nested quantifiers on user input
- [ ] All cases run and pass (table shown)
- [ ] Token-by-token explanation
- [ ] Usage snippet with correct escaping
- [ ] Limits stated
```

## Anti-Patterns (What NOT to do)

* **Delivering a pattern without running it** — "it should work" is how validators accept garbage.
* **Unanchored validators** — `\d{5}` happily matches inside `"abc941031xyz"` with `search`.
* **Flavor-specific syntax without checking the engine** — lookbehind in older JavaScript, backreferences in RE2.
* **Parsing HTML, JSON, or nested structures with regex** — use a parser.
* **A 200-character pattern where two simple checks in code would be clearer** — readability is a feature.
* **`\d` and `\w` on user input in Python without `re.ASCII`** — they match non-ASCII digits and letters.

## Examples

### Example 1: a validator

**User:** "Regex for US ZIP codes — 5 digits or ZIP+4 — in Python."

**Expected output:**

```text
$ python3 scripts/test_regex.py '^\d{5}(?:-\d{4})?$' --flags ASCII \
    --match 94103 94103-1234 00501 \
    --no-match 9410 941031 94103-123 "94103 1234" " 94103" "" "９４１０３"

input         expected   result
'94103'       match      pass
'94103-1234'  match      pass
'00501'       match      pass
'9410'        no match   pass
'941031'      no match   pass
'94103-123'   no match   pass
'94103 1234'  no match   pass
' 94103'      no match   pass
''            no match   pass
'９４１０３'   no match   pass   ← full-width digits rejected because of re.ASCII
10/10 cases pass

| Token        | Meaning                        |
|--------------|--------------------------------|
| ^ … $        | the whole string               |
| \d{5}        | exactly five digits (ASCII)    |
| (?:-\d{4})?  | optionally a hyphen + 4 digits |

import re
ZIP = re.compile(r"^\d{5}(?:-\d{4})?$", re.ASCII)
def is_zip(value: str) -> bool:
    return ZIP.fullmatch(value.strip()) is not None

Limit: checks the format only, not whether the ZIP code exists.
```

### Example 2: a slow regex

**User:** "This email check hangs our API on some inputs: `^([a-zA-Z0-9]+\.?)+@example\.com$`"

**Expected output:**

```text
Cause: ([a-zA-Z0-9]+\.?)+ is a nested quantifier — when the dot is absent, the inner + and outer +
can split "aaaa…" in exponentially many ways, and a failing input (no "@example.com") forces the
engine to try them all.

$ python3 scripts/test_regex.py '^([a-zA-Z0-9]+\.?)+@example\.com$' --no-match "aaaaaaaaaaaaaaaaaaaaaaaaaaaa!"
'aaaaaaaaaaaaaaaaaaaaaaaaaaaa!'  no match  pass  (5990 ms — slow)   ← 29 characters, 6 seconds
warning: nested quantifier like (a+)+ can backtrack catastrophically on long inputs

Fix — each repetition must start with a dot, so there's only one way to match:
^[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*@example\.com$

$ python3 scripts/test_regex.py '^[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*@example\.com$' \
    --match a@example.com a.b@example.com first.last2@example.com \
    --no-match .a@example.com a.@example.com a..b@example.com a@example.org "aaaaaaaaaaaaaaaaaaaaaaaaaaaa!"
8/8 cases pass, all under 1 ms.

Also: cap input length (e.g. 254 chars) before matching, and for general email validation use a
library plus a confirmation email rather than a regex.
```

## Quick Reference

| Need | Pattern idea |
|---|---|
| Whole value only | `^…$` / `fullmatch` / `\A…\z` |
| Text between quotes | `"([^"]*)"` |
| Optional part | `(?:…)?` |
| ASCII digits only (Python) | `\d` with `re.ASCII`, or `[0-9]` |
| One-of list | `(?:red|green|blue)` |
| Repeated separated items | `item(?:,item)*` — not `(item,?)*` |
| Structured input (HTML, JSON, URLs) | Use a parser, not a regex |
