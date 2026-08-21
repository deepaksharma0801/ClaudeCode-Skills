# Awesome Claude Skills [![Awesome](https://awesome.re/badge-flat.svg)](https://awesome.re)

> A curated blueprint of the best Claude **Skills**, **MCP servers**, and **Claude Code plugins** on GitHub — from official Anthropic repositories to the heaviest-hitting community directories.

Skills are *procedural knowledge*: reusable instruction sets that Claude loads on demand. MCP servers are *access*: connections to databases, APIs, and tools. Plugins *extend the CLI*. This repo keeps the three cleanly separated so you can find what you need fast.

## Contents

- [How Skills Work](#how-skills-work)
- [Core Mega-Repositories](#core-mega-repositories-the-hall-of-fame)
- [Top Standalone Skills](#top-standalone-skills)
  - [Development & Code](#development--code)
  - [Research & Data Analysis](#research--data-analysis)
  - [Communication & Branding](#communication--branding)
- [Essential MCP Servers](#essential-mcp-servers)
- [Claude Code Plugins](#claude-code-plugins)
- [Repository Layout](#repository-layout)
- [Writing Your Own Skill](#writing-your-own-skill)
- [Contributing](#contributing)

## How Skills Work

Skills use a **progressive disclosure architecture**: the metadata (name + description) loads first, and the full instruction set loads only when Claude determines the skill applies to the task at hand. That makes the `description` field the single most important line in a skill — it is the trigger.

Keep instructions declarative, keep them scoped, and include few-shot examples so Claude knows what success looks like. See [`templates/SKILL_TEMPLATE.md`](templates/SKILL_TEMPLATE.md).

## Core Mega-Repositories (The Hall of Fame)

The primary source repositories driving the Claude ecosystem.

| Repository | What's in it |
| --- | --- |
| [anthropics/skills](https://github.com/anthropics/skills) | **Official.** The standard agent skills specification, document-creation skills (`docx`, `pdf`, `pptx`, `xlsx`), and skill templates. |
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | A massive directory of 1,000+ practical skills and plugins, handling auth and connections to 1,000+ apps via the Composio gateway. |
| [GetBindu/awesome-claude-code-and-skills](https://github.com/GetBindu/awesome-claude-code-and-skills) | 67 MIT-licensed skills, 368 persona-based skills (e.g. `startup-cto`), 76 expert agents, and 859 Python tools. |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | Heavily starred community list covering progressive disclosure architecture, UI workflows, and skill vetting. |
| [ai-for-developers/awesome-claude](https://github.com/ai-for-developers/awesome-claude) | SDKs, agent frameworks (LangGraph, CrewAI), and prompt architectures for Claude. |
| [win4r/Awesome-Claude-MCP-Servers](https://github.com/win4r/Awesome-Claude-MCP-Servers) | The premier curated list of Model Context Protocol servers optimized for Claude. |

## Top Standalone Skills

### Development & Code

- **web-artifacts-builder** — Instructs Claude on building complex web apps for the claude.ai interface using React, Tailwind CSS, and shadcn/ui.
- **root-cause-tracing** — A methodical skill for when errors surface deep in execution: forces Claude to trace backward to the original trigger instead of patching the symptom.
- **ios-simulator-skill** — Lets Claude Code drive the iOS Simulator directly, preferring navigation via accessibility APIs over screenshots for better performance.
- **test-fixing** — Detects failing tests automatically and proposes patches or fixes.

### Research & Data Analysis

- **recursive-research** — Autonomous research up to PhD level, with source tiering, Munger inversion for autonomous decisions, and disk checkpointing to survive context compaction.
- **csv-data-summarizer-claude-skill** — Analyzes CSV files for columns, distributions, missing data, and correlations without requiring user prompts.

### Communication & Branding

- **brand-guidelines** — Applies official brand colors, fonts, and typography to artifacts for a consistent visual identity.
- **internal-comms** — Writes company newsletters, status reports, and FAQs using company-specific formats.

## Essential MCP Servers

| Integration | Description |
| --- | --- |
| [`@modelcontextprotocol/server-postgres`](https://github.com/modelcontextprotocol/servers) | Executes safe, read-only SQL queries against PostgreSQL databases with schema inspection. |
| [`@modelcontextprotocol/server-memory`](https://github.com/modelcontextprotocol/servers) | Gives Claude a knowledge-graph-based persistent memory system. |
| [`@modelcontextprotocol/server-github`](https://github.com/modelcontextprotocol/servers) | Official integration for reading repositories, issues, and PRs via the GitHub API. |
| [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) | Real-time web search using the Exa AI Search API. |

## Claude Code Plugins

- **backlog** — Pure TypeScript plugin providing persistent cross-session task management, with 24 MCP tools for managing dependencies and docs.
- **AgentLint** — Runs 33 evidence-backed checks across your repository to ensure it is optimized for AI-agent compatibility.
- **mcp-builder** — Guides the creation of high-quality MCP servers for integrating external APIs and services with LLMs.

## Repository Layout

```text
ClaudeCode-OneShot/
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── skills/
│   ├── development/
│   ├── data-and-analysis/
│   ├── business-and-comms/
│   └── security-and-qa/
├── mcp-servers/
│   ├── databases/
│   └── tools-and-utils/
├── claude-code-plugins/
└── templates/
    └── SKILL_TEMPLATE.md
```

Procedural knowledge (Skills) stays separate from external integrations (MCPs) and terminal workflows (Plugins).

## Writing Your Own Skill

Every skill must follow the official YAML frontmatter specification so it works in both the Claude web interface and the Claude Code CLI:

```markdown
---
name: your-skill-name
description: A clear, concise description of what the skill does and exactly when Claude should invoke it (max 200 characters).
dependencies: python>=3.8, pandas>=1.5.0
---

# Detailed Instructions
```

Copy [`templates/SKILL_TEMPLATE.md`](templates/SKILL_TEMPLATE.md) into the right category folder under `skills/` and fill it in.

## Contributing

PRs welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first — every submission is vetted against the template and the description-quality bar. By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Content in this repository is released under [CC0 1.0](LICENSE) (public domain). Linked projects retain their own licenses.
