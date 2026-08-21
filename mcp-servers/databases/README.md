# Database MCP Servers

| Server | Description |
| --- | --- |
| [`@modelcontextprotocol/server-postgres`](https://github.com/modelcontextprotocol/servers) | Safe, read-only SQL queries against PostgreSQL, with schema inspection. |

## Example configuration

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    }
  }
}
```

Never commit a connection string containing credentials. Use an environment variable and reference
it from your local config.
