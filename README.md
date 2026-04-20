# z3rno-mcp

MCP (Model Context Protocol) server that exposes [Z3rno](https://z3rno.dev) memory operations as tools. Gives any MCP-compatible AI client (Claude Desktop, Cursor, Windsurf, etc.) the ability to store, recall, forget, and audit agent memories.

## Tools

| Tool | Description |
|------|-------------|
| `z3rno.store` | Store a memory (fact, preference, decision, etc.) |
| `z3rno.recall` | Semantic search over stored memories |
| `z3rno.forget` | Soft delete or GDPR-compliant hard delete |
| `z3rno.audit` | Query the audit log of memory operations |

## Installation

```bash
# With uv (recommended)
uv pip install z3rno-mcp

# With pip
pip install z3rno-mcp
```

## Configuration

Set environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `Z3RNO_API_KEY` | Yes | — | Your Z3rno API key |
| `Z3RNO_BASE_URL` | No | `https://api.z3rno.dev` | Z3rno server URL |
| `Z3RNO_AGENT_ID` | No | — | Default agent ID (can be overridden per-call) |

## Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "z3rno": {
      "command": "z3rno-mcp",
      "env": {
        "Z3RNO_API_KEY": "z3rno_sk_...",
        "Z3RNO_AGENT_ID": "my-agent"
      }
    }
  }
}
```

If installed via `uv`, use the full path:

```json
{
  "mcpServers": {
    "z3rno": {
      "command": "uv",
      "args": ["run", "z3rno-mcp"],
      "env": {
        "Z3RNO_API_KEY": "z3rno_sk_...",
        "Z3RNO_AGENT_ID": "my-agent"
      }
    }
  }
}
```

## Cursor

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "z3rno": {
      "command": "z3rno-mcp",
      "env": {
        "Z3RNO_API_KEY": "z3rno_sk_...",
        "Z3RNO_AGENT_ID": "my-agent"
      }
    }
  }
}
```

## Claude Code

```bash
claude mcp add z3rno -- z3rno-mcp
```

Then set environment variables in your shell profile or `.env`.

## Local Development

```bash
# Clone and install
git clone https://github.com/the-ai-project-co/z3rno-mcp.git
cd z3rno-mcp
uv sync --dev

# Run directly
Z3RNO_API_KEY=z3rno_sk_test Z3RNO_BASE_URL=http://localhost:8000 uv run z3rno-mcp

# Lint and format
uv run ruff check .
uv run ruff format .
```

## License

Apache-2.0
