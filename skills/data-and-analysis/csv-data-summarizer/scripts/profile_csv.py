#!/usr/bin/env python3
"""Profile a CSV/TSV: shape, inferred types, nulls, uniques, numeric stats, top values, quality
flags, and strong correlations. Standard library only (Python 3.8+).

Usage:
    python3 profile_csv.py data.csv
    python3 profile_csv.py data.tsv --max-rows 200000 --corr 0.5

The delimiter is sniffed (comma, tab, semicolon, pipe). Values like "", "NA", "N/A", "null",
"None", "NaN", "-" count as missing. Prints Markdown.
"""
import argparse
import csv
import math
import re
import statistics
import sys
from collections import Counter
from datetime import datetime

MISSING = {"", "na", "n/a", "null", "none", "nan", "-", "#n/a"}
NUM_LIKE = re.compile(r"^[\s$€£]*-?[\d,]*\.?\d+\s*%?$")
DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")
BOOLS = {"true", "false", "yes", "no", "y", "n", "0", "1", "t", "f"}

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def to_float(v):
    try:
        return float(v)
    except ValueError:
        return None


def is_date(v):
    v = v.strip().replace("Z", "")
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(v[:19], fmt)
            return True
        except ValueError:
            pass
    return False


def infer(values):
    """values: non-missing strings. Returns (type, notes)."""
    if not values:
        return "empty", []
    sample = values[:5000]
    if all(to_float(v) is not None for v in sample):
        return ("int" if all(re.fullmatch(r"-?\d+", v.strip()) for v in sample) else "float"), []
    num_like = sum(1 for v in sample if NUM_LIKE.match(v))
    if num_like >= 0.9 * len(sample):
        odd = len(sample) - num_like
        return "text", ["numbers stored as text (currency symbols, commas, or %)"
                        + (f"; {odd:,} value(s) in the sample aren't numeric" if odd else "")]
    if all(v.strip().lower() in BOOLS for v in sample) and len({v.strip().lower() for v in sample}) <= 2:
        return "bool", []
    if sum(is_date(v) for v in sample[:500]) >= 0.95 * min(len(sample), 500):
        return "date/time (as text)", ["parse as a date before time analysis"]
    return "text", []


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def fmt(x):
    if x is None:
        return "—"
    if abs(x) >= 1000 or x == int(x):
        return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:g}"
    return f"{x:,.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--max-rows", type=int, default=0, help="profile only the first N rows (0 = all)")
    ap.add_argument("--corr", type=float, default=0.5, help="report correlations with |r| >= this")
    args = ap.parse_args()

    with open(args.path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        head = fh.read(64 * 1024)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(head, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(fh, dialect)
        header = next(reader, None)
        if not header:
            raise SystemExit("error: file is empty")
        cols = [[] for _ in header]
        row_counter = Counter()
        rows = ragged = 0
        for row in reader:
            if args.max_rows and rows >= args.max_rows:
                break
            if len(row) != len(header):
                ragged += 1
                row = (row + [""] * len(header))[:len(header)]
            row_counter[tuple(row)] += 1
            for i, v in enumerate(row):
                cols[i].append(v)
            rows += 1

    sep = {",": "comma", "\t": "tab", ";": "semicolon", "|": "pipe"}.get(dialect.delimiter, repr(dialect.delimiter))
    print(f"## Structure\n{rows:,} rows x {len(header)} columns ({sep}-separated)"
          + (f", first {rows:,} rows only" if args.max_rows and rows >= args.max_rows else ""))

    profiles, quality, numeric = [], [], {}
    for name, values in zip(header, cols):
        present = [v for v in values if v.strip().lower() not in MISSING]
        nulls = rows - len(present)
        typ, notes = infer(present)
        uniq = len(set(present))
        profiles.append((name, typ, len(present), nulls, uniq))
        pct = nulls / rows if rows else 0
        if pct > 0.2:
            quality.append(f"`{name}`: {pct:.1%} missing ({nulls:,} of {rows:,})")
        if uniq == 1 and rows > 1:
            quality.append(f"`{name}`: constant (only value {present[0]!r})")
        if uniq == len(present) == rows and typ == "text" and rows > 1:
            quality.append(f"`{name}`: unique on every row (likely an ID)")
        for n in notes:
            quality.append(f"`{name}`: {n}")
        if typ in ("int", "float"):
            numeric[name] = [to_float(v) if v.strip().lower() not in MISSING else None for v in values]

    print("\n| column | type | non-null | missing | unique |\n|---|---|---|---|---|")
    for name, typ, nn, nulls, uniq in profiles:
        print(f"| {name} | {typ} | {nn:,} | {nulls:,} | {uniq:,} |")

    dups = sum(c - 1 for c in row_counter.values() if c > 1)
    if dups:
        quality.append(f"{dups:,} exact duplicate rows")
    if ragged:
        quality.append(f"{ragged:,} rows with the wrong number of fields (padded/truncated)")
    print("\n## Data quality")
    print("\n".join(f"- {q}" for q in quality) if quality else "- No issues flagged.")

    print("\n## Distributions")
    for name, vals in numeric.items():
        xs = [v for v in vals if v is not None]
        if xs:
            sd = statistics.pstdev(xs) if len(xs) > 1 else 0.0
            print(f"- {name}: min {fmt(min(xs))}, median {fmt(statistics.median(xs))}, "
                  f"max {fmt(max(xs))}, mean {fmt(statistics.fmean(xs))}, std {fmt(sd)}")
    for (name, typ, nn, nulls, uniq), values in zip(profiles, cols):
        if typ in ("text", "bool") and 0 < uniq <= 20:
            counts = Counter(v for v in values if v.strip().lower() not in MISSING).most_common()
            print(f"- {name}: " + " / ".join(f"{k} {c:,}" for k, c in counts))
        elif typ == "text" and uniq > 20 and uniq < nn:
            top = Counter(v for v in values if v.strip().lower() not in MISSING).most_common(5)
            print(f"- {name}: {uniq:,} distinct; top: " + ", ".join(f"{k} ({c:,})" for k, c in top))

    pairs = []
    names = list(numeric)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = numeric[names[i]], numeric[names[j]]
            xy = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
            r = pearson([x for x, _ in xy], [y for _, y in xy]) if xy else None
            if r is not None and abs(r) >= args.corr:
                pairs.append((abs(r), names[i], names[j], r, len(xy)))
    print(f"\n## Correlations (|r| >= {args.corr})")
    if pairs:
        for _, a, b, r, n in sorted(pairs, reverse=True):
            print(f"- {a} ~ {b}: r = {r:.2f} (n = {n:,})")
    else:
        print("- None above the threshold.")


if __name__ == "__main__":
    main()
