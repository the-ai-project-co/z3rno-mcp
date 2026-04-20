# Quickstart: z3rno-mcp

A detailed getting-started guide for the Z3rno MCP (Model Context Protocol) server.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A running Z3rno server (local or hosted)
- A Z3rno API key
- An MCP-compatible client (Claude Desktop, Cursor, Windsurf, Claude Code)

If you do not have a Z3rno server running, see the [z3rno-server quickstart](https://github.com/the-ai-project-co/z3rno-server/blob/main/QUICKSTART.md) to set one up locally with Docker Compose.

## Step-by-step Installation

### 1. Install the MCP server

```bash
# With uv (recommended)
uv pip install z3rno-mcp

# With pip
pip install z3rno-mcp
```

### 2. Set environment variables

```bash
export Z3RNO_API_KEY="z3rno_sk_test_localdev"
export Z3RNO_BASE_URL="http://localhost:8000"
export Z3RNO_AGENT_ID="my-agent"
```

### 3. Configure your MCP client

#### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "z3rno": {
      "command": "z3rno-mcp",
      "env": {
        "Z3RNO_API_KEY": "z3rno_sk_test_localdev",
        "Z3RNO_BASE_URL": "http://localhost:8000",
        "Z3RNO_AGENT_ID": "my-agent"
      }
    }
  }
}
```

If installed via uv:

```json
{
  "mcpServers": {
    "z3rno": {
      "command": "uv",
      "args": ["run", "z3rno-mcp"],
      "env": {
        "Z3RNO_API_KEY": "z3rno_sk_test_localdev",
        "Z3RNO_BASE_URL": "http://localhost:8000",
        "Z3RNO_AGENT_ID": "my-agent"
      }
    }
  }
}
```

#### Claude Code

```bash
claude mcp add z3rno -- z3rno-mcp
```

#### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "z3rno": {
      "command": "z3rno-mcp",
      "env": {
        "Z3RNO_API_KEY": "z3rno_sk_test_localdev",
        "Z3RNO_BASE_URL": "http://localhost:8000",
        "Z3RNO_AGENT_ID": "my-agent"
      }
    }
  }
}
```

## Running Locally

### Test the MCP server directly

```bash
Z3RNO_API_KEY=z3rno_sk_test_localdev \
Z3RNO_BASE_URL=http://localhost:8000 \
z3rno-mcp
```

The server communicates over stdio (MCP protocol). You will not see human-readable output -- it is waiting for JSON-RPC messages from an MCP client.

### Verify it works in Claude Desktop

1. Restart Claude Desktop after updating config
2. Look for the hammer icon in the chat input area
3. Click it to see the available Z3rno tools: `z3rno.store`, `z3rno.recall`, `z3rno.forget`, `z3rno.audit`
4. Ask Claude: "Store a memory that I prefer dark mode"
5. Then ask: "What do you remember about my preferences?"

## First Working Example

Once configured in Claude Desktop, try this conversation:

> **You:** Remember that my favorite programming language is Rust and I prefer functional patterns.

Claude will use `z3rno.store` to save this.

> **You:** What do you know about my coding preferences?

Claude will use `z3rno.recall` to search stored memories and respond with what it finds.

## Development

To work on z3rno-mcp itself:

```bash
git clone https://github.com/the-ai-project-co/z3rno-mcp.git
cd z3rno-mcp
uv sync --dev

# Run directly
Z3RNO_API_KEY=z3rno_sk_test Z3RNO_BASE_URL=http://localhost:8000 uv run z3rno-mcp

# Lint and test
uv run ruff check .
uv run ruff format .
uv run pytest
```

## Common Issues / Troubleshooting

### 1. Claude Desktop does not show the hammer icon

- Ensure the config JSON is valid (no trailing commas)
- Restart Claude Desktop completely (Cmd+Q, not just close window)
- Check the MCP server logs in `~/Library/Logs/Claude/mcp*.log`

### 2. "z3rno-mcp: command not found"

The binary is not on your PATH. Either use the full path or the `uv run` variant in your config:

```bash
which z3rno-mcp  # Should print a path
```

If using uv, ensure uv is on your PATH and use the `"command": "uv", "args": ["run", "z3rno-mcp"]` form.

### 3. "Connection refused" from MCP server

The Z3rno server is not running at `Z3RNO_BASE_URL`. Start it:

```bash
# In z3rno-server repo
docker compose -f docker-compose.dev.yml up
```

### 4. "401 Unauthorized" errors in MCP logs

The API key is wrong. For local development, use `z3rno_sk_test_localdev`.

### 5. Tools appear but never return results

Check that your Z3rno server has the OpenAI API key configured (needed for embedding generation during recall). Check server logs for errors.
