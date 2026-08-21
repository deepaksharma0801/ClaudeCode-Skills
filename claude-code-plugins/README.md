# Claude Code Plugins

Plugins extend the Claude Code CLI ecosystem: extra commands, hooks, and bundled MCP tools.

| Plugin | Description |
| --- | --- |
| **backlog** | Pure TypeScript plugin for persistent cross-session task management, exposing 24 MCP tools for dependencies and docs. |
| **AgentLint** | Runs 33 evidence-backed checks across a repository to verify it is optimized for AI-agent compatibility. |
| **mcp-builder** | Guides the creation of high-quality MCP servers for integrating external APIs with LLMs. |

Plugins are installed from a marketplace inside Claude Code. Prefer plugins that state exactly which
tools and hooks they register — an opaque plugin is an opaque expansion of what your agent can do.
