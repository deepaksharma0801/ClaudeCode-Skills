#!/usr/bin/env python3
"""Check every skills/**/SKILL.md against the Agent Skills spec and this repo's review bar.

Spec: https://agentskills.io/specification
Repo rules: CONTRIBUTING.md

Usage: python3 scripts/validate_skills.py   (exit code 1 if any skill fails)
No dependencies beyond the standard library.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Agent Skills spec
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # lowercase, digits, single hyphens
MAX_NAME = 64
MAX_COMPATIBILITY = 500
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# Repo rules (stricter than the spec's 1,024-character description limit)
MAX_DESCRIPTION = 200
MAX_BODY_LINES = 500
REQUIRED_SECTIONS = [
    r"^# Detailed Instructions",
    r"^## Overview",
    r"^## Workflow Rules",
    r"^## Anti-Patterns",
    r"^## Examples",
]
# Bundled files mentioned in SKILL.md, e.g. `scripts/check.py` or (references/locks.md)
BUNDLED_REF_RE = re.compile(r"(?<![\w/.-])((?:scripts|references|assets|evals)/[\w./-]+\.\w+)")


def parse_frontmatter(text):
    """Return (top-level fields, body). Indented lines belong to the previous key (e.g. metadata)."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fields = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[0] in " \t":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"frontmatter line is not 'key: value': {line!r}")
        fields[key.strip()] = value.strip().strip("\"'")
    return fields, text[end + 4:]


def check_sections(body):
    errors = []
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


def check_evals(skill_dir, name):
    path = skill_dir / "evals" / "evals.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"evals/evals.json is not valid JSON: {exc}"]
    errors = []
    if data.get("skill_name") != name:
        errors.append(f"evals/evals.json skill_name {data.get('skill_name')!r} does not match {name!r}")
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        return errors + ["evals/evals.json has no 'evals' list"]
    ids = [e.get("id") for e in evals]
    if len(ids) != len(set(ids)):
        errors.append("evals/evals.json has duplicate ids")
    for e in evals:
        if not e.get("prompt") or not e.get("expected_output"):
            errors.append(f"eval {e.get('id')!r} needs 'prompt' and 'expected_output'")
        for f in e.get("files", []):
            if not (skill_dir / f).exists():
                errors.append(f"eval {e.get('id')!r} references missing file {f!r}")
    return errors


def check(path):
    try:
        text = path.read_text(encoding="utf-8")
        fields, body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]
    if fields is None:
        return ["missing YAML frontmatter (file must start with '---')"]

    errors = []
    unknown = sorted(set(fields) - ALLOWED_FIELDS)
    if unknown:
        errors.append(f"unknown frontmatter field(s) {unknown}; allowed: {sorted(ALLOWED_FIELDS)}")

    name = fields.get("name", "")
    if not name:
        errors.append("missing 'name'")
    elif len(name) > MAX_NAME or not NAME_RE.match(name):
        errors.append(f"name {name!r} must be 1-{MAX_NAME} chars of a-z, 0-9 and single hyphens")
    elif name != path.parent.name:
        errors.append(f"name {name!r} does not match folder {path.parent.name!r}")

    description = fields.get("description", "")
    if not description:
        errors.append("missing 'description'")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"description is {len(description)} chars (max {MAX_DESCRIPTION})")

    compatibility = fields.get("compatibility")
    if compatibility is not None and not 1 <= len(compatibility) <= MAX_COMPATIBILITY:
        errors.append(f"compatibility must be 1-{MAX_COMPATIBILITY} chars")

    lines = text.count("\n") + 1
    if lines > MAX_BODY_LINES:
        errors.append(f"SKILL.md is {lines} lines (keep under {MAX_BODY_LINES}; move detail to references/)")

    errors += check_sections(body)

    # Only the instructions; examples may mention files in the user's own project.
    instructions = re.split(r"^## Examples", body, maxsplit=1, flags=re.MULTILINE)[0]
    for ref in sorted(set(BUNDLED_REF_RE.findall(instructions))):
        if not (path.parent / ref).exists():
            errors.append(f"SKILL.md mentions {ref!r} but the file does not exist")

    errors += check_evals(path.parent, name)
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
