# Contributing

Thanks for helping build this. Two kinds of contributions are accepted:

1. **A link** to an existing skill, MCP server, or plugin — added to the curated lists in the README.
2. **A skill** that lives in this repo, under the correct `skills/<category>/` folder.

## Adding a link

- One entry per pull request where possible.
- Use the format `**name** — one sentence on what it does and when to reach for it.`
- Say what the thing *is*, not how great it is. No marketing copy.
- The project must be public, working, and maintained. Dead links and abandoned repos get removed.

## Adding a skill

1. Copy `templates/SKILL_TEMPLATE.md` to `skills/<category>/<your-skill-name>/SKILL.md`.
2. Categories: `development`, `data-and-analysis`, `business-and-comms`, `security-and-qa`.
3. Fill in every section. A skill with an empty Examples section will not be merged.

### Frontmatter rules

| Field | Required | Rules |
| --- | --- | --- |
| `name` | yes | 1–64 characters: lowercase letters, digits, and single hyphens; no leading or trailing hyphen; matches the folder name |
| `description` | yes | ≤ 200 characters in this repo (the spec allows 1,024); states **what it does** and **when Claude should use it** |
| `compatibility` | no | ≤ 500 characters; only when the skill needs specific tools, e.g. `Requires Python 3.8+ with pandas.` |
| `license` | no | short license name, or a bundled license file |
| `metadata` | no | string-to-string map, e.g. `version`, `author` |
| `allowed-tools` | no | experimental; space-separated tool list, e.g. `Bash(git:*) Read` |

These follow the [Agent Skills specification](https://agentskills.io/specification). Any other
frontmatter field fails validation.

### Bundled files

A skill folder can include more than `SKILL.md`. Keep `SKILL.md` under 500 lines and move detail
into these, referenced one level deep:

| Folder | For |
| --- | --- |
| `scripts/` | Code Claude runs for deterministic steps (stdlib-only where possible; print helpful errors) |
| `references/` | Longer docs Claude reads only when needed |
| `assets/` | Templates, schemas, and data files used in the output |
| `evals/evals.json` | Realistic test prompts and expectations, in the [skill-creator format](https://github.com/anthropics/skills/blob/main/skills/skill-creator/references/schemas.md) |

The `description` is the trigger. Because of progressive disclosure, Claude reads only the metadata
until it decides the skill applies — a vague description means the skill never fires, no matter how
good the instructions are.

Good: `Analyzes CSV files for column types, distributions, missing data, and correlations. Use when a user shares a CSV or asks for a data profile.`

Bad: `A powerful skill for data work.`

### Body rules

Every skill is written against the quality bar in [docs/QUALITY.md](docs/QUALITY.md). In short:

- State the core principle and **why** it matters; Claude follows reasons more reliably than bare rules.
- Say when to use the skill **and when not to**.
- Steps explain their purpose and give exact commands where a step is fragile.
- Include a copyable checklist, and for discipline skills, red flags and a rationalizations table.
- Every anti-pattern has a one-line why.
- At least two examples (a full worked example plus an edge case), with numbers that add up.
- End with a quick-reference table. Keep `SKILL.md` under 500 lines; move depth to `references/`.
- `evals/evals.json` with at least three prompts, one targeting the failure the skill prevents.

## Checklist before opening a PR

- [ ] Frontmatter parses as valid YAML
- [ ] `python3 scripts/validate_skills.py` passes
- [ ] `description` is under 200 characters and names its trigger condition
- [ ] Folder name matches `name`
- [ ] All template sections filled in
- [ ] Tested in Claude Code or the Claude web interface at least once
- [ ] README list updated if you added an entry

## Review

Maintainers vet each submission against the template and the description bar above. Expect
feedback on the `description` field most often — it is the part that decides whether the skill
is ever used.
