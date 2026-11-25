---
name: readme-writer
description: Writes or rewrites a project README from the actual code with a pitch, a working quickstart, usage examples, and configuration. Use when a repo needs a README or its README is stale.
---

# Detailed Instructions

A README has one job: get a stranger from "what is this?" to "it works on my machine" in a few
minutes. Write it from the code, not from memory: every command in the quickstart must be one
you found in the repo (package scripts, Makefile, Dockerfile, CI config) and, where possible,
ran. A README with a broken first command loses most readers at that command.

## When to Use

- "Write a README for this repo" / "our README is out of date"
- Preparing a project to be open-sourced or shared with another team
- A library or CLI that people keep asking the same setup questions about
- Reviewing a README draft before a release

**Don't use when:** the reader is a new teammate who needs the architecture (use
`codebase-onboarding`), the content is API reference for every function (generate it from
docstrings instead), or it's a changelog (use `release-notes-writer`).

## Overview

READMEs fail by opening with history or badges instead of what the project does, by listing
install steps that no longer work, and by never showing a real example. This skill reads the
repo to find what the project is, how it's installed, run, configured, and tested, then writes a
README in a fixed order (pitch, quickstart, usage, configuration, development, license) and
verifies the quickstart commands before handing it over.

## Workflow Rules

### 1. Learn the project from the code

1. Read the manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`), entry points,
   `Makefile`/scripts, `Dockerfile`, `.env.example`, CI workflows, and any existing docs. CI is
   the most reliable record of how the project is actually built and tested.
2. Identify the **audience**: users of a library, users of a CLI or app, or contributors. The
   top of the README serves users; contributor details go lower or in `CONTRIBUTING.md`.
3. Find the real **prerequisites**: language version (from the manifest or CI matrix), system
   packages, services (Postgres, Redis), and accounts or API keys.

### 2. Write in this order

4. **Name + one-line pitch:** what it does and for whom, in plain words ("Generates typed API
   clients from OpenAPI specs for TypeScript projects"). Then 2–3 bullets on why someone would
   use it.
5. **Quickstart:** the shortest path to a visible result — install, minimal config, one command,
   and what output to expect. Copy-pasteable code blocks, one command per line.
6. **Usage:** 2–4 real examples covering the common tasks, with output. Use realistic values,
   not `foo`.
7. **Configuration:** a table of options or env vars — name, default, what it does — taken from
   the code or `.env.example`. Never print real secret values.
8. **Development:** how to run tests, lint, and the app locally, from the CI config.
9. **License** and where to get help (issues, discussions). Add badges only if they're accurate
   (CI status, version, license) and keep them to one line.

### 3. Verify

10. Run the quickstart and test commands in a clean environment if possible (fresh venv or
    container). If a command can't be run here, say which ones are unverified.
11. Check every relative link and image path exists.
12. Keep it short enough to read in about 3 minutes; move long material to `docs/` and link it.

## Output shape

```markdown
# <name>
<one-line pitch>
- why 1 / why 2 / why 3
## Quickstart        prerequisites, install, run, expected output
## Usage             2–4 real examples
## Configuration     table: option | default | description
## Development       test, lint, run locally
## License
```

## Checklist

```text
- [ ] Manifest, scripts, Dockerfile, .env.example, CI read
- [ ] Audience chosen; user content first
- [ ] Pitch says what and for whom in one line
- [ ] Quickstart reaches a visible result; prerequisites with versions
- [ ] Usage examples are realistic and show output
- [ ] Configuration table matches the code
- [ ] Commands verified (or marked unverified); links checked
- [ ] No secrets; badges accurate
```

## Anti-Patterns (What NOT to do)

* **Commands copied from memory or other projects** — use what the repo actually runs.
* **Opening with history, motivation essays, or a wall of badges** — the reader wants to know what it is.
* **`foo`/`bar` examples** — they don't show what the tool is for.
* **Documenting options that don't exist** (or missing ones that do) — read them from the code.
* **Everything in one 2,000-line README** — link to `docs/` for depth.
* **Real keys or internal URLs in examples** — use placeholders.

## Examples

### Example 1: a Python CLI

**User:** "Write a README for this repo." *(pyproject.toml declares `csvlint` with a console script,
`requires-python = ">=3.10"`; CI runs `pytest` and `ruff check`.)*

**Expected output:**

````markdown
# csvlint

Checks CSV files against a schema before they reach your pipeline — catches missing columns,
bad types, and duplicate keys in seconds.

- One YAML schema per file type; no code needed
- Clear line-and-column error messages
- Exit code 1 on failure, so it drops into CI

## Quickstart

Requires Python 3.10+.

```bash
pip install csvlint
csvlint check orders.csv --schema schemas/orders.yaml
```

```text
orders.csv:14:3  amount  "12,50" is not a decimal
orders.csv:27:1  order_id  duplicate value "A-1042" (first seen on line 9)
2 errors in 1,204 rows
```

## Usage

Check every CSV in a folder:
```bash
csvlint check data/*.csv --schema schemas/orders.yaml
```

Generate a starter schema from an existing file:
```bash
csvlint infer orders.csv > schemas/orders.yaml
```

## Configuration

| Option | Default | Description |
|---|---|---|
| `--schema` | (required) | Path to the YAML schema |
| `--max-errors` | `100` | Stop after this many errors |
| `--format` | `text` | `text` or `json` output |

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
````

Verified: `pip install -e ".[dev]"`, `pytest` (42 passed), and the quickstart command against
`tests/fixtures/orders.csv`.

### Example 2: reviewing a stale README

**User:** "Is our README OK?" *(It says `npm start`; package.json has no `start` script, only `dev`
and `build`. It lists `API_URL` but the code reads `VITE_API_URL`.)*

**Expected output:**

```text
Two things will break a new user's first five minutes:
1. Quickstart says `npm start` — package.json has no start script. Use `npm run dev`.
2. Config lists `API_URL`; src/config.ts reads `import.meta.env.VITE_API_URL`. Users setting
   API_URL will hit the default localhost URL silently.

Also: the top paragraph is project history; move it down and lead with what the app does.
Want me to rewrite it in the standard order?
```

## Quick Reference

| Section | Source of truth |
|---|---|
| Pitch | What the code does, for whom |
| Prerequisites | Manifest + CI matrix |
| Quickstart | Package scripts / Makefile, run and verified |
| Usage | Real commands with real output |
| Configuration | `.env.example`, config loader, CLI parser |
| Development | CI workflow steps |
| Length | ~3 minutes to read; depth in `docs/` |
