#!/usr/bin/env python3
"""Pseudonymize, mask, generalize, or drop columns in a CSV. Standard library only (Python 3.8+).

Usage:
    python3 anonymize.py in.csv out.csv --rules rules.json
    python3 anonymize.py in.csv out.csv --rules rules.json --report      # also print a summary

rules.json maps column name -> action:
    {
      "email":       "hash",          keyed HMAC-SHA256 pseudonym (same input -> same token)
      "user_id":     "hash",
      "name":        "drop",          remove the column
      "phone":       "mask",          keep the last 2 characters, replace the rest with '*'
      "birth_date":  "year",          2026-03-14 -> 2026
      "signup_at":   "month",         2026-03-14T10:22:00 -> 2026-03
      "zip":         "zip3",          94103 -> 941**
      "age":         "bucket:10",     37 -> 30-39
      "ip":          "ip24",          203.0.113.42 -> 203.0.113.0
      "notes":       "redact"         free text -> emails, phone numbers, long digit runs replaced
    }
Columns not listed are copied unchanged, and listed in the report so nothing slips through.

The HMAC key comes from the ANONYMIZE_KEY environment variable. Keep it secret and out of the
output: anyone with the key can re-identify hashed values by hashing candidates. Without the
variable, a random key is generated per run (tokens are then not stable across runs).
"""
import argparse
import csv
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
from collections import Counter

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
LONG_DIGITS = re.compile(r"\b\d{6,}\b")


def make_actions(key):
    def hash_(v):
        if not v:
            return v
        return "anon_" + hmac.new(key, v.strip().lower().encode(), hashlib.sha256).hexdigest()[:16]

    def mask(v):
        return v if len(v) <= 2 else "*" * (len(v) - 2) + v[-2:]

    def year(v):
        m = re.match(r"\s*(\d{4})", v)
        return m.group(1) if m else ""

    def month(v):
        m = re.match(r"\s*(\d{4})-(\d{2})", v)
        return f"{m.group(1)}-{m.group(2)}" if m else ""

    def zip3(v):
        digits = re.sub(r"\D", "", v)
        return digits[:3] + "**" if len(digits) >= 5 else ""

    def ip24(v):
        parts = v.strip().split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            return ".".join(parts[:3] + ["0"])
        if ":" in v:  # IPv6: keep the /48 prefix
            return ":".join(v.strip().split(":")[:3]) + "::"
        return ""

    def redact(v):
        v = EMAIL.sub("[email]", v)
        v = PHONE.sub("[phone]", v)
        return LONG_DIGITS.sub("[number]", v)

    return {"hash": hash_, "mask": mask, "year": year, "month": month, "zip3": zip3,
            "ip24": ip24, "redact": redact}


def bucket(size):
    def f(v):
        try:
            n = int(float(v))
        except ValueError:
            return ""
        lo = n // size * size
        return f"{lo}-{lo + size - 1}"
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--rules", required=True, help="JSON file mapping column -> action")
    ap.add_argument("--report", action="store_true", help="print columns handled/unhandled and k-anonymity check")
    ap.add_argument("--quasi", help="comma-separated output columns to check k-anonymity on (e.g. zip,age,gender)")
    args = ap.parse_args()

    with open(args.rules, encoding="utf-8") as fh:
        rules = json.load(fh)
    env_key = os.environ.get("ANONYMIZE_KEY")
    key = env_key.encode() if env_key else secrets.token_bytes(32)
    actions = make_actions(key)

    funcs = {}
    for col, action in rules.items():
        if action == "drop":
            continue
        if action.startswith("bucket:"):
            funcs[col] = bucket(int(action.split(":", 1)[1]))
        elif action in actions:
            funcs[col] = actions[action]
        else:
            raise SystemExit(f"error: unknown action {action!r} for column {col!r}; "
                             f"use one of {sorted(actions) + ['drop', 'bucket:N']}")

    with open(args.input, newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        columns = reader.fieldnames or []
        missing = [c for c in rules if c not in columns]
        if missing:
            raise SystemExit(f"error: rules mention columns not in the file: {missing}; columns are {columns}")
        out_cols = [c for c in columns if rules.get(c) != "drop"]
        quasi = [c.strip() for c in args.quasi.split(",")] if args.quasi else []
        groups = Counter()
        rows = 0
        with open(args.output, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_cols)
            writer.writeheader()
            for row in reader:
                out = {c: (funcs[c](row[c] or "") if c in funcs else row[c]) for c in out_cols}
                writer.writerow(out)
                if quasi:
                    groups[tuple(out.get(q, "") for q in quasi)] += 1
                rows += 1

    if args.report or quasi:
        untouched = [c for c in columns if c not in rules]
        print(f"rows: {rows}")
        print(f"transformed: {', '.join(f'{c} ({rules[c]})' for c in rules)}")
        print(f"copied unchanged: {', '.join(untouched) if untouched else '(none)'}")
        if quasi:
            k = min(groups.values()) if groups else 0
            small = sum(n for n in groups.values() if n < 5)
            print(f"k-anonymity on ({', '.join(quasi)}): k = {k}; "
                  f"{small} row(s) in groups smaller than 5")
        if not env_key:
            print("note: ANONYMIZE_KEY not set; used a random key, so hashes are not stable across runs",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
