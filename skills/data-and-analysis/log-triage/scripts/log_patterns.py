#!/usr/bin/env python3
"""Group log lines into templates and rank them by count, with first/last seen times.

Usage:
    python3 log_patterns.py app.log
    python3 log_patterns.py app.log --level ERROR,WARN --top 20
    kubectl logs deploy/api --since=2h | python3 log_patterns.py - --after 2026-11-20T13:55
    python3 log_patterns.py app.log --json-field message --json-level-field level   # JSON lines

Variable parts (UUIDs, hex IDs, emails, IPs, URLs' query strings, numbers, quoted strings) are
replaced with placeholders so repeated events collapse into one template. Timestamps are read from
the start of each line (ISO 8601 or "YYYY-MM-DD HH:MM:SS") or from a JSON field.
Standard library only (Python 3.8+). Output never includes the original variable values.
"""
import argparse
import json
import re
import sys
from collections import defaultdict

TS = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")
LEVEL = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|ERR|CRITICAL|FATAL|PANIC)\b", re.I)
NORMALIZERS = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<UUID>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<EMAIL>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<IP>"),
    (re.compile(r"\b(?:bearer|token|api[_-]?key|access[_-]?key|secret|password|passwd|authorization)[=: ]+\S+", re.I), "<SECRET>"),
    (re.compile(r"\?[^\s\"']+"), "?<QUERY>"),
    (re.compile(r"\b[0-9a-f]{12,}\b", re.I), "<HEX>"),
    (re.compile(r"\"[^\"]{0,200}\"|'[^']{0,200}'"), "<STR>"),
    (re.compile(r"(?<![A-Za-z])-?\d+(?:\.\d+)?(?:ms|s|MB|KB|GB|%)?\b"), "<N>"),
]


def normalize(msg):
    msg = TS.sub("", msg, count=1)
    for rx, repl in NORMALIZERS:
        msg = rx.sub(repl, msg)
    return re.sub(r"\s+", " ", msg).strip()[:220]


def norm_level(lv):
    lv = (lv or "").upper()
    return {"WARNING": "WARN", "ERR": "ERROR", "CRITICAL": "FATAL", "PANIC": "FATAL"}.get(lv, lv or "-")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="log file, or - for stdin")
    ap.add_argument("--level", help="comma-separated levels to keep, e.g. ERROR,WARN")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--after", help="only lines at/after this timestamp (ISO 8601 prefix)")
    ap.add_argument("--before", help="only lines before this timestamp")
    ap.add_argument("--json-field", help="for JSON lines: field holding the message")
    ap.add_argument("--json-level-field", default="level")
    ap.add_argument("--json-time-field", default="timestamp")
    args = ap.parse_args()
    keep = {norm_level(l) for l in args.level.split(",")} if args.level else None

    stats = defaultdict(lambda: {"count": 0, "first": None, "last": None})
    levels = defaultdict(int)
    total = kept = 0
    fh = sys.stdin if args.path == "-" else open(args.path, encoding="utf-8", errors="replace")
    with fh:
        for line in fh:
            total += 1
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if args.json_field:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = str(rec.get(args.json_field, ""))
                lv = norm_level(str(rec.get(args.json_level_field, "")))
                ts = str(rec.get(args.json_time_field, ""))[:19].replace(" ", "T") or None
            else:
                m = TS.search(line[:40])
                ts = m.group(1).replace(" ", "T") if m else None
                lm = LEVEL.search(line[:120])
                lv = norm_level(lm.group(1) if lm else "")
                msg = line
            if args.after and ts and ts < args.after:
                continue
            if args.before and ts and ts >= args.before:
                continue
            levels[lv] += 1
            if keep and lv not in keep:
                continue
            kept += 1
            key = (lv, normalize(msg))
            s = stats[key]
            s["count"] += 1
            if ts:
                s["first"] = ts if s["first"] is None or ts < s["first"] else s["first"]
                s["last"] = ts if s["last"] is None or ts > s["last"] else s["last"]

    print(f"Lines read: {total:,}. By level: " + ", ".join(f"{k} {v:,}" for k, v in sorted(levels.items(), key=lambda x: -x[1])))
    print(f"Patterns: {len(stats):,} from {kept:,} lines" + (f" (levels {args.level})" if keep else ""))
    ranked = sorted(stats.items(), key=lambda kv: -kv[1]["count"])[: args.top]
    print(f"\n| # | level | count | first seen | last seen | template |\n|---|---|---|---|---|---|")
    for i, ((lv, tmpl), s) in enumerate(ranked, 1):
        t = tmpl.replace("|", "\\|")
        print(f"| {i} | {lv} | {s['count']:,} | {s['first'] or '—'} | {s['last'] or '—'} | {t} |")
    starts = [s["first"] for s in stats.values() if s["first"]]
    window_start = min(starts) if starts else None
    onset = sorted(((s["first"], lv, tmpl, s["count"]) for (lv, tmpl), s in stats.items()
                    if s["first"] and lv in ("ERROR", "FATAL", "WARN")), key=lambda x: x[0])
    background = [o for o in onset if o[0][:16] == (window_start or "")[:16]]
    new = [o for o in onset if o not in background]
    if new:
        print("\nWARN/ERROR patterns that START during the window, earliest first (likely first cause at top):")
        for first, lv, tmpl, n in new[:5]:
            print(f"- {first}  {lv}  ({n:,}x)  {tmpl[:120]}")
    if background:
        print("\nPresent from the start of the window (probably background noise; compare with an earlier period):")
        for first, lv, tmpl, n in background[:5]:
            print(f"- {lv}  ({n:,}x)  {tmpl[:120]}")


if __name__ == "__main__":
    main()
