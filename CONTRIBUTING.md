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
| `name` | yes | lowercase, kebab-case, matches the folder name |
| `description` | yes | ≤ 200 characters; states **what it does** and **when Claude should invoke it** |
| `dependencies` | no | comma-separated, with version constraints (`python>=3.8, pandas>=1.5.0`) |

The `description` is the trigger. Because of progressive disclosure, Claude reads only the metadata
until it decides the skill applies — a vague description means the skill never fires, no matter how
good the instructions are.

Good: `Analyzes CSV files for column types, distributions, missing data, and correlations. Use when a user shares a CSV or asks for a data profile.`

Bad: `A powerful skill for data work.`

### Body rules

- Write instructions as directives, not prose.
- Include an **Anti-Patterns** section. What Claude should *not* do is often more load-bearing than what it should.
- Include at least one worked example with the exact expected output format.
- Keep the full instruction set tight. Push reference material into separate files the skill can point to.

## Checklist before opening a PR

- [ ] Frontmatter parses as valid YAML
- [ ] `description` is under 200 characters and names its trigger condition
- [ ] Folder name matches `name`
- [ ] All template sections filled in
- [ ] Tested in Claude Code or the Claude web interface at least once
- [ ] README list updated if you added an entry

## Review

Maintainers vet each submission against the template and the description bar above. Expect
feedback on the `description` field most often — it is the part that decides whether the skill
is ever used.
