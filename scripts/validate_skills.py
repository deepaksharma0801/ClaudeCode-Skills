#!/usr/bin/env python3
"""Check every skills/**/SKILL.md against the review bar in CONTRIBUTING.md.

Usage: python3 scripts/validate_skills.py   (exit code 1 if any skill fails)
No dependencies beyond the standard library.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_DESCRIPTION = 200
REQUIRED_SECTIONS = [
    r"^# Detailed Instructions",
    r"^## Overview",
    r"^## Workflow Rules",
    r"^## Anti-Patterns",
    r"^## Examples",
]


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fields = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"frontmatter line is not 'key: value': {line!r}")
        fields[key.strip()] = value.strip().strip("\"'")
    return fields, text[end + 4:]


def check(path):
    errors = []
    try:
        fields, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [str(exc)]
    if fields is None:
        return ["missing YAML frontmatter (file must start with '---')"]

    name = fields.get("name", "")
    if not name:
        errors.append("missing 'name'")
    elif not NAME_RE.match(name):
        errors.append(f"name {name!r} is not kebab-case")
    elif name != path.parent.name:
        errors.append(f"name {name!r} does not match folder {path.parent.name!r}")

    description = fields.get("description", "")
    if not description:
        errors.append("missing 'description'")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"description is {len(description)} chars (max {MAX_DESCRIPTION})")

    for pattern in REQUIRED_SECTIONS:
        match = re.search(pattern + r".*$", body, re.MULTILINE)
        if not match:
            errors.append(f"missing section matching {pattern[1:]!r}")
            continue
        rest = body[match.end():]
        nxt = re.search(r"^#{1,2} ", rest, re.MULTILINE)
        if not rest[: nxt.start() if nxt else len(rest)].strip():
            errors.append(f"section {match.group(0).strip()!r} is empty")
    return errors


def main():
    skills = sorted((ROOT / "skills").rglob("SKILL.md"))
    if not skills:
        print("no SKILL.md files found under skills/")
        return 1
    failed = 0
    for path in skills:
        errors = check(path)
        rel = path.relative_to(ROOT)
        if errors:
            failed += 1
            print(f"FAIL {rel}")
            for err in errors:
                print(f"     - {err}")
        else:
            print(f"ok   {rel}")
    print(f"\n{len(skills) - failed}/{len(skills)} skills pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
