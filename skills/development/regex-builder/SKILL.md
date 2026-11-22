---
name: regex-builder
description: Builds a regular expression from a plain description and proves it with matching and non-matching test cases. Use when a user asks for a regex, or to fix or explain one that is not matching.
---

# Detailed Instructions

No regex is delivered without test cases that were actually run. Write the tests first, then the
pattern, then show which cases pass.

## Overview

Regexes look right and fail on the edges: an unanchored pattern that matches substrings, a greedy
`.*` that eats too much, a flavor-specific feature that the user's engine does not support. This
skill pins down the flavor, writes examples that must and must not match, builds the pattern, runs
it, and explains it piece by piece.

## Workflow Rules

1. **Flavor:** determine the engine (JavaScript, Python `re`, PCRE, Go RE2, POSIX grep/sed, .NET).
   Ask once if unclear and it matters (lookbehind, named groups, `\d` Unicode behavior).
2. **Test cases first:** at least 5 strings that must match and 5 that must not, including edge
   cases (empty string, leading/trailing spaces, near-misses, Unicode if relevant).
3. **Build** the simplest pattern that passes. Anchor with `^…$` (or `\b`) when matching whole
   values. Prefer explicit character classes over `.`; prefer lazy or negated classes over
   greedy `.*`.
4. **Run it** in the target language (a short script) against every case, and show a pass/fail
   table. Iterate until all pass.
5. **Explain** the pattern token by token in a small table.
6. **Usage snippet** in the user's language, with the right escaping (raw strings in Python, double
   escaping in JSON or Java strings).
7. **Limits:** say plainly what the regex does not handle (e.g. full RFC 5322 email validation) and
   suggest a parser or library when a regex is the wrong tool (HTML, nested structures, dates).
8. Flag catastrophic backtracking risks (nested quantifiers like `(a+)+`) on user input.

## Anti-Patterns (What NOT to do)

* Do not deliver a pattern you have not run against test cases.
* Do not use flavor-specific syntax (lookbehind in older JS, backreferences in RE2) without checking the engine.
* Do not leave whole-value validators unanchored.
* Do not parse HTML, JSON, or nested brackets with regex when a parser is available.
* Do not write a 200-character pattern when two simple checks in code are clearer.

## Examples

**User:** "Regex for US ZIP codes, 5 digits or ZIP+4, in Python."

**Expected output:**

```text
Pattern (Python re):  ^\d{5}(?:-\d{4})?$

| Input        | Expected | Result |
|--------------|----------|--------|
| 94103        | match    | pass   |
| 94103-1234   | match    | pass   |
| 00501        | match    | pass   |
| 9410         | no match | pass   |
| 941031       | no match | pass   |
| 94103-123    | no match | pass   |
| 94103 1234   | no match | pass   |
| " 94103"     | no match | pass   |
| ""           | no match | pass   |
| ９４１０３ (full-width) | no match | pass (uses re.ASCII) |

| Token        | Meaning                          |
|--------------|----------------------------------|
| ^ … $        | whole string only                |
| \d{5}        | exactly five digits              |
| (?:-\d{4})?  | optional hyphen + four digits    |

import re
ZIP = re.compile(r"^\d{5}(?:-\d{4})?$", re.ASCII)
ZIP.fullmatch(value.strip())

Limit: checks format only, not whether the ZIP code exists.
```
