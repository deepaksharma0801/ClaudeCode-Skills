# Tools & Utilities MCP Servers

| Server | Description |
| --- | --- |
| [`@modelcontextprotocol/server-memory`](https://github.com/modelcontextprotocol/servers) | Knowledge-graph-based persistent memory across sessions. |
| [`@modelcontextprotocol/server-github`](https://github.com/modelcontextprotocol/servers) | Official GitHub integration for repositories, issues, and PRs. |
| [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) | Real-time web search via the Exa AI Search API. |

## Example configuration

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": { "EXA_API_KEY": "${EXA_API_KEY}" }
    }
  }
}
```

Keep API keys in environment variables, not in the committed config.
