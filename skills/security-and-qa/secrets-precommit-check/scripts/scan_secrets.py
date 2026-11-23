#!/usr/bin/env python3
"""Scan the lines a commit or push would add for credentials. Standard library only (Python 3.8+).

Usage (run inside the repository):
    python3 scan_secrets.py                       # staged changes (git diff --cached)
    python3 scan_secrets.py --range origin/main..HEAD   # commits about to be pushed
    python3 scan_secrets.py --files config.py .env      # whole files, not a diff

Only added lines are checked. Findings show file:line, the type, and a redacted preview (first 4
characters) — the full value is never printed. A line containing `pragma: allowlist secret`
is skipped (same convention as detect-secrets).
Exit code: 1 if anything is found, 0 if clean, 2 on usage errors.
"""
import argparse
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import PurePosixPath

PROVIDER_PATTERNS = [
    ("AWS access key ID", re.compile(r"\b((?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16})\b")),
    ("GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b")),
    ("Anthropic API key", re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{20,})")),
    ("OpenAI API key", re.compile(r"\b(sk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,})")),
    ("Slack token", re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})")),
    ("Google API key", re.compile(r"\b(AIza[0-9A-Za-z_-]{35})")),
    ("Stripe live key", re.compile(r"\b((?:sk|rk)_live_[0-9A-Za-z]{20,})")),
    ("Private key", re.compile(r"(-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----)")),
    ("JSON Web Token", re.compile(r"\b(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")),
    ("Connection string with password", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]{3,})@")),
]
GENERIC = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|client[_-]?secret|api[_-]?key|apikey|access[_-]?key|auth[_-]?token|token)\b"
    r"[\"']?\s*[:=]\s*(?:\"([^\"]{12,})\"|'([^']{12,})'|([^\s\"',;#]{12,}))")
PLACEHOLDER = re.compile(
    r"(?i)(^<.*>$|^\$\{.*\}$|^\{\{.*\}\}$|your[_-]|example|changeme|placeholder|dummy|fake|sample|"
    r"xxxx|\*\*\*\*|^test|redacted|process\.env|os\.environ|getenv|env\[|secrets\.|vault:|ssm:)")
RISKY_NAMES = re.compile(
    r"(^|/)(\.env(\.[\w-]+)?|id_rsa|id_ed25519|credentials\.json|service[-_]account[\w-]*\.json|"
    r"[\w.-]+\.(pem|key|p12|pfx|jks|keystore)|[\w.-]+\.tfstate(\.backup)?)$")
SAFE_ENV = re.compile(r"\.env\.(example|sample|template|dist)$")
ALLOW = "pragma: allowlist secret"


def entropy(s):
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())


def redact(v):
    return v[:4] + "…" if len(v) > 4 else "…"


def git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("error: git not found")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"error: git {' '.join(args)} failed: {exc.stderr.strip()}")


def added_lines_from_diff(diff):
    """Yield (path, line_number, text) for added lines in a unified diff with -U0."""
    path, line = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            yield path, line, raw[1:]
            line += 1


def scan_line(path, n, text):
    if ALLOW in text:
        return []
    found = []
    for name, rx in PROVIDER_PATTERNS:
        for m in rx.finditer(text):
            value = m.group(1)
            if name != "Private key" and PLACEHOLDER.search(value):
                continue  # documentation samples such as AKIAIOSFODNN7EXAMPLE, ${DB_PASSWORD}
            found.append((path, n, name, redact(value)))
    if not found:
        for m in GENERIC.finditer(text):
            value = m.group(2) or m.group(3) or m.group(4)
            if PLACEHOLDER.search(value) or entropy(value) < 3.0:
                continue
            found.append((path, n, f"Possible secret ({m.group(1)})", redact(value)))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--range", help="commit range to scan, e.g. origin/main..HEAD")
    g.add_argument("--files", nargs="+", help="scan whole files instead of a diff")
    args = ap.parse_args()

    findings, files = [], set()
    if args.files:
        for f in args.files:
            files.add(f)
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    for i, text in enumerate(fh, 1):
                        findings += scan_line(f, i, text.rstrip("\n"))
            except OSError as exc:
                print(f"warning: cannot read {f}: {exc}", file=sys.stderr)
        scope = f"{len(args.files)} file(s)"
    else:
        diff_args = ["diff", "-U0", "--no-color", args.range] if args.range else ["diff", "--cached", "-U0", "--no-color"]
        name_args = ["diff", "--name-only", "--diff-filter=AM", args.range] if args.range else ["diff", "--cached", "--name-only", "--diff-filter=AM"]
        files = set(filter(None, git(*name_args).splitlines()))
        lines = list(added_lines_from_diff(git(*diff_args)))
        for path, n, text in lines:
            findings += scan_line(path, n, text)
        scope = (f"range {args.range}" if args.range else "staged changes") + f" ({len(files)} files, +{len(lines)} lines)"

    for f in sorted(files):
        if RISKY_NAMES.search(f) and not SAFE_ENV.search(f):
            findings.insert(0, (f, "-", "Risky file", "should this be committed at all?"))

    print(f"Scanned: {scope}")
    for path, n, kind, preview in findings:
        print(f"  {path}:{n}  {kind:<34} {preview}")
    if findings:
        print(f"\nBLOCKED — {len(findings)} finding(s). Remove or move to env vars / a secret manager.")
        print(f"False positive? Add '{ALLOW}' to that line.")
        return 1
    print("SAFE TO COMMIT — no secrets found in added lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
