#!/usr/bin/env python3
"""Test a regular expression against cases that must and must not match (Python `re` flavor).

Usage:
    python3 test_regex.py '^\\d{5}(?:-\\d{4})?$' --match 94103 94103-1234 --no-match 9410 941031
    python3 test_regex.py PATTERN --cases cases.json       # {"match": [...], "no_match": [...]}
    python3 test_regex.py PATTERN --cases cases.json --mode search --flags IGNORECASE,ASCII

--mode fullmatch (default) checks the whole string; search finds the pattern anywhere.
Also warns about nested quantifiers that can backtrack catastrophically on user input.
Exit code: 0 if every case passes, 1 otherwise. Standard library only (Python 3.8+).
"""
import argparse
import json
import re
import sys
import time

# A repeated group whose body *starts* with a repeated atom, e.g. (a+)+, ([a-z]+\.?)*, (\w+\s?)*.
# Repetitions can then split the same text many ways. A group that starts with a required literal,
# like (?:\.[a-z]+)*, is not flagged.
REPEATED_GROUP = re.compile(r"\((?:\?:)?((?:\\.|\[[^\]]*\]|[^()\\])*)\)(?:[+*]|\{\d*,\d*\})")
STARTS_REPEATED = re.compile(r"^(?:\\.|\[[^\]]*\]|[^\\\[])[+*]")


def risky_nesting(pattern):
    return any(STARTS_REPEATED.match(m.group(1)) for m in REPEATED_GROUP.finditer(pattern))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern")
    ap.add_argument("--match", nargs="*", default=[], help="strings that must match")
    ap.add_argument("--no-match", nargs="*", default=[], help="strings that must not match")
    ap.add_argument("--cases", help='JSON file: {"match": [...], "no_match": [...]}')
    ap.add_argument("--mode", choices=["fullmatch", "search", "match"], default="fullmatch")
    ap.add_argument("--flags", default="", help="comma-separated re flags, e.g. IGNORECASE,ASCII,MULTILINE")
    args = ap.parse_args()

    must, must_not = list(args.match), list(args.no_match)
    if args.cases:
        with open(args.cases, encoding="utf-8") as fh:
            data = json.load(fh)
        must += data.get("match", [])
        must_not += data.get("no_match", [])
    if not must and not must_not:
        ap.error("give cases with --match/--no-match or --cases")

    flags = 0
    for name in filter(None, (f.strip().upper() for f in args.flags.split(","))):
        if not hasattr(re, name):
            ap.error(f"unknown flag {name}")
        flags |= getattr(re, name)
    try:
        rx = re.compile(args.pattern, flags)
    except re.error as exc:
        print(f"error: pattern does not compile: {exc}")
        return 1
    test = getattr(rx, args.mode)

    rows, failures = [], 0
    for expected, cases in ((True, must), (False, must_not)):
        for case in cases:
            start = time.perf_counter()
            got = test(case) is not None
            ms = (time.perf_counter() - start) * 1000
            ok = got == expected
            failures += not ok
            rows.append((repr(case), "match" if expected else "no match", "pass" if ok else "FAIL", ms))

    width = max(len(r[0]) for r in rows)
    print(f"Pattern ({args.mode}{', ' + args.flags if args.flags else ''}): {args.pattern}\n")
    print(f"{'input'.ljust(width)}  expected   result")
    for case, expected, result, ms in rows:
        slow = f"  ({ms:.0f} ms — slow)" if ms > 50 else ""
        print(f"{case.ljust(width)}  {expected:<9}  {result}{slow}")
    if risky_nesting(args.pattern):
        print("\nwarning: nested quantifier like (a+)+ can backtrack catastrophically on long inputs")
    print(f"\n{len(rows) - failures}/{len(rows)} cases pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
