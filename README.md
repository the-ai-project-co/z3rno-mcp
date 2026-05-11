# z3rno-mcp

[![PyPI](https://img.shields.io/pypi/v/z3rno-mcp)](https://pypi.org/project/z3rno-mcp/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/the-ai-project-co/z3rno-mcp/actions/workflows/release.yml/badge.svg)](https://github.com/the-ai-project-co/z3rno-mcp/actions/workflows/release.yml)

MCP (Model Context Protocol) server that exposes [Z3rno](https://z3rno.dev) memory operations as tools. Gives any MCP-compatible AI client (Claude Desktop, Cursor, Windsurf, etc.) the ability to store, recall, forget, and audit agent memories.

## Tools

| Tool | Description |
|------|-------------|
| `z3rno.store` | Store a memory (fact, preference, decision, etc.) |
| `z3rno.recall` | Semantic search over stored memories |
| `z3rno.forget` | Soft delete or GDPR-compliant hard delete |
| `z3rno.audit` | Query the audit log of memory operations |
| `z3rno.ingest` | Accept text/URL into the Forge pipeline |
| `z3rno.distill` | Build/extend the graph from stored memories |
| `z3rno.refine` | Improve the graph in place |
| `z3rno.visualize_url` | Build a graph-viewer URL |
| `z3rno.start_conversation` | Open a session for turn-aware recall (Phase G) |
| `z3rno.end_conversation` | Mark a session ended (Phase G) |
| `z3rno.summarize_conversation` | Fetch turn history for LLM summarization (Phase G) |
| `z3rno.time_travel` | Recall at a past timestamp via SCD-2 temporal index (Phase G) |

## Installation

```bash
# Zero-install run — same UX as npx for Python tools
uvx z3rno-mcp

# Pin into a project
uv pip install z3rno-mcp

# Or with pip
pip install z3rno-mcp
```

### Claude Code plugin

A plugin manifest at `claude-code-plugin/plugin.json` pins `uvx z3rno-mcp` and declares all twelve tools. Point Claude Code at it and set `Z3RNO_API_KEY` before launch.

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

For a detailed step-by-step setup, see [QUICKSTART.md](QUICKSTART.md).

Full documentation: [astron-bb4261fd.mintlify.app](https://astron-bb4261fd.mintlify.app)

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
