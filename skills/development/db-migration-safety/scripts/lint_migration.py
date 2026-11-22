#!/usr/bin/env python3
"""Flag PostgreSQL migration statements that take heavy locks, rewrite tables, or break running code.

Usage:
    python3 lint_migration.py migration.sql [more.sql ...]
    cat migration.sql | python3 lint_migration.py -

Exit code: 1 if any ERROR is found, else 0. Standard library only (Python 3.8+).
This is a pattern linter: it does not know table sizes or traffic, so treat a clean result as
"no known risky pattern", not as proof of safety.
"""
import re
import sys

RULES = [
    # (rule id, severity, regex on a normalized statement, message)
    ("index-not-concurrent", "ERROR",
     r"^create\s+(unique\s+)?index\s+(?!concurrently\b)",
     "CREATE INDEX without CONCURRENTLY blocks writes while it builds"),
    ("drop-index-not-concurrent", "WARN",
     r"^drop\s+index\s+(?!concurrently\b)",
     "DROP INDEX without CONCURRENTLY takes an ACCESS EXCLUSIVE lock"),
    ("volatile-default", "ERROR",
     r"\badd\s+(column\s+)?\S+\s+[^;]*\bdefault\s+(gen_random_uuid|uuid_generate_v\d|random|clock_timestamp|timeofday)\s*\(",
     "ADD COLUMN with a volatile DEFAULT rewrites the whole table under ACCESS EXCLUSIVE"),
    ("column-type-change", "ERROR",
     r"\balter\s+column\s+\S+\s+(set\s+data\s+)?type\b",
     "ALTER COLUMN ... TYPE usually rewrites the table and its indexes under ACCESS EXCLUSIVE"),
    ("set-not-null", "WARN",
     r"\balter\s+column\s+\S+\s+set\s+not\s+null\b",
     "SET NOT NULL scans the table under ACCESS EXCLUSIVE unless a validated CHECK (col IS NOT NULL) exists"),
    ("constraint-validates", "ERROR",
     r"\badd\s+constraint\s+\S+\s+(foreign\s+key|check)\b(?![^;]*\bnot\s+valid\b)",
     "FOREIGN KEY / CHECK without NOT VALID scans the table while holding locks"),
    ("unique-without-index", "ERROR",
     r"\badd\s+(constraint\s+\S+\s+)?(unique|primary\s+key)\b(?![^;]*\busing\s+index\b)",
     "ADD UNIQUE / PRIMARY KEY builds an index under lock; build it CONCURRENTLY and use USING INDEX"),
    ("breaking-rename", "ERROR",
     r"\brename\s+(?!constraint\b)(column\s+)?\S+\s+to\b",
     "RENAME COLUMN breaks app instances still using the old name"),
    ("breaking-rename-table", "ERROR",
     r"^alter\s+table\s+\S+\s+rename\s+to\b",
     "RENAME TABLE breaks app instances still using the old name"),
    ("drop-column", "WARN",
     r"\bdrop\s+column\b",
     "DROP COLUMN breaks app instances that still read it; ship the code change first"),
    ("drop-table", "WARN",
     r"^drop\s+table\b",
     "DROP TABLE is irreversible and breaks code that still uses it"),
    ("unbatched-write", "WARN",
     r"^(update|delete\s+from)\s+\S+(?![^;]*\bwhere\b)",
     "UPDATE/DELETE without WHERE rewrites every row in one transaction; batch by primary key"),
    ("table-rewrite-maintenance", "ERROR",
     r"^(vacuum\s+full|cluster)\b",
     "VACUUM FULL / CLUSTER lock the table for the whole rewrite"),
]

LOCKING_ALTER = re.compile(r"^alter\s+table\b")
LOCK_TIMEOUT = re.compile(r"^set\s+(local\s+)?lock_timeout\b")
CONCURRENT = re.compile(r"\bconcurrently\b")
TXN_START = re.compile(r"^(begin|start\s+transaction)\b")


def statements(sql):
    """Yield (line_number, normalized_statement), skipping comments and string contents."""
    sql = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), sql, flags=re.S)
    line, start_line, buf = 1, 1, []
    in_str = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if not in_str and sql.startswith("--", i):
            j = sql.find("\n", i)
            i = len(sql) if j == -1 else j
            continue
        if ch == "'":
            in_str = not in_str
        if ch == "\n":
            line += 1
        if ch == ";" and not in_str:
            text = " ".join("".join(buf).split()).lower()
            if text:
                yield start_line, text
            buf, start_line = [], line
        else:
            if not buf and ch.isspace():
                start_line = line
            else:
                buf.append(ch)
        i += 1
    text = " ".join("".join(buf).split()).lower()
    if text:
        yield start_line, text


def lint(name, sql):
    findings = []
    stmts = list(statements(sql))
    has_lock_timeout = any(LOCK_TIMEOUT.search(s) for _, s in stmts)
    in_txn = False
    for line, stmt in stmts:
        if TXN_START.search(stmt):
            in_txn = True
        elif stmt in ("commit", "end", "rollback"):
            in_txn = False
        for rule, severity, pattern, message in RULES:
            if re.search(pattern, stmt):
                findings.append((line, severity, rule, message))
        if in_txn and CONCURRENT.search(stmt):
            findings.append((line, "ERROR", "concurrently-in-transaction",
                             "CONCURRENTLY cannot run inside a transaction block"))
    if not has_lock_timeout and any(LOCKING_ALTER.search(s) for _, s in stmts):
        findings.append(("*", "WARN", "no-lock-timeout",
                         "ALTER TABLE without SET lock_timeout; a blocked migration will queue all traffic"))
    return [(name, *f) for f in findings]


def main(argv):
    paths = argv[1:] or ["-"]
    all_findings = []
    for path in paths:
        try:
            sql = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        all_findings += lint("stdin" if path == "-" else path, sql)
    for name, line, severity, rule, message in all_findings:
        print(f"{name}:{line}  {severity:<5}  {rule:<26} {message}")
    errors = sum(1 for f in all_findings if f[2] == "ERROR")
    warns = len(all_findings) - errors
    print(f"\n{errors} error(s), {warns} warning(s)" if all_findings else "No risky patterns found.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
