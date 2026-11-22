#!/usr/bin/env python3
"""Build a cohort retention table from an event log CSV. Standard library only (Python 3.8+).

Each user's cohort is the period of their first event (or of --cohort-col, e.g. signup time).
Cell (cohort, N) = share of the cohort active in period N after the cohort period ("classic"
retention). Periods that have not fully elapsed yet are left blank, so recent cohorts don't show
a fake drop-off.

Usage:
    python3 retention.py events.csv --user-col user_id --time-col occurred_at
    python3 retention.py events.csv --user-col user_id --time-col ts --period month --max-periods 6
    python3 retention.py events.csv ... --cohort-col signed_up_at --format csv > retention.csv

Timestamps: ISO 8601 ("2026-01-05", "2026-01-05 10:00:00", "2026-01-05T10:00:00Z").
Only the date part is used, in the time zone the data is stored in.
"""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta


def parse_date(value, column, row_number):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            raise SystemExit(f"error: row {row_number}: cannot parse {column}={value!r} as an ISO 8601 date")


def period_start(d, period):
    if period == "week":
        return d - timedelta(days=d.weekday())  # Monday
    return d.replace(day=1)


def periods_between(start, d, period):
    if period == "week":
        return (period_start(d, "week") - start).days // 7
    return (d.year - start.year) * 12 + (d.month - start.month)


def add_periods(start, n, period):
    if period == "week":
        return start + timedelta(weeks=n)
    month = start.month - 1 + n
    return date(start.year + month // 12, month % 12 + 1, 1)


def build(rows, user_col, time_col, cohort_col, period):
    activity = defaultdict(set)   # user -> set of period starts with activity
    cohort_of = {}                 # user -> cohort period start
    last_date = None
    for i, row in enumerate(rows, start=2):
        for col in [user_col, time_col] + ([cohort_col] if cohort_col else []):
            if col not in row:
                raise SystemExit(f"error: column {col!r} not found; columns are {sorted(row)}")
        user = row[user_col].strip()
        if not user or not row[time_col].strip():
            continue
        d = parse_date(row[time_col], time_col, i)
        last_date = d if last_date is None or d > last_date else last_date
        activity[user].add(period_start(d, period))
        if cohort_col and row[cohort_col].strip():
            cohort_of[user] = period_start(parse_date(row[cohort_col], cohort_col, i), period)
    if not activity:
        raise SystemExit("error: no rows with both a user and a timestamp")
    for user, periods in activity.items():
        cohort_of.setdefault(user, min(periods))
    return activity, cohort_of, last_date


def table(activity, cohort_of, last_date, period, max_periods):
    members = defaultdict(set)
    for user, cohort in cohort_of.items():
        members[cohort].add(user)
    results = []
    for cohort in sorted(members):
        users = members[cohort]
        cells = []
        for n in range(max_periods + 1):
            start = add_periods(cohort, n, period)
            end = add_periods(cohort, n + 1, period) - timedelta(days=1)
            if end > last_date:      # period not complete yet
                cells.append(None)
                continue
            active = sum(1 for u in users if start in activity[u])
            cells.append(active / len(users))
        results.append((cohort, len(users), cells))
    return results


def weighted_average(results, max_periods):
    avg = []
    for n in range(max_periods + 1):
        num = sum(size * cells[n] for _, size, cells in results if cells[n] is not None)
        den = sum(size for _, size, cells in results if cells[n] is not None)
        avg.append(num / den if den else None)
    return avg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", help="event log CSV ('-' for stdin)")
    ap.add_argument("--user-col", required=True)
    ap.add_argument("--time-col", required=True)
    ap.add_argument("--cohort-col", help="optional column with the cohort date (e.g. signup); default: first event")
    ap.add_argument("--period", choices=["week", "month"], default="week")
    ap.add_argument("--max-periods", type=int, default=8)
    ap.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    args = ap.parse_args()

    handle = sys.stdin if args.csv_path == "-" else open(args.csv_path, newline="", encoding="utf-8")
    with handle:
        activity, cohort_of, last_date = build(csv.DictReader(handle), args.user_col, args.time_col,
                                               args.cohort_col, args.period)
    results = table(activity, cohort_of, last_date, args.period, args.max_periods)
    avg = weighted_average(results, args.max_periods)

    label = "W" if args.period == "week" else "M"
    header = ["cohort", "users"] + [f"{label}{n}" for n in range(args.max_periods + 1)]
    fmt = lambda v: "" if v is None else f"{v * 100:.1f}%"
    body = [[c.isoformat(), str(size)] + [fmt(v) for v in cells] for c, size, cells in results]
    body.append(["weighted avg", str(sum(s for _, s, _ in results))] + [fmt(v) for v in avg])

    if args.format == "csv":
        w = csv.writer(sys.stdout)
        w.writerow(header)
        w.writerows(body)
    else:
        print("| " + " | ".join(header) + " |")
        print("|" + "|".join(["---"] * len(header)) + "|")
        for row in body:
            print("| " + " | ".join(row) + " |")
        print(f"\nData through {last_date.isoformat()}. Blank = period not complete yet. "
              f"{len(cohort_of)} users, {len(results)} cohorts.")


if __name__ == "__main__":
    main()
