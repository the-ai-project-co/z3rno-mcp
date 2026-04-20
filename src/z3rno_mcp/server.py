"""Z3rno MCP server — thin wrapper around the z3rno Python SDK.

Exposes four tools over MCP stdio transport:
  - z3rno.store   — store a memory
  - z3rno.recall  — semantic recall
  - z3rno.forget  — soft or GDPR hard delete
  - z3rno.audit   — query audit log

Configuration via environment variables:
  - Z3RNO_BASE_URL  (default: https://api.z3rno.dev)
  - Z3RNO_API_KEY   (required)
  - Z3RNO_AGENT_ID  (optional default agent ID)
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from z3rno import Z3rnoClient

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "z3rno",
    description="Z3rno AI agent memory — store, recall, forget, and audit memories.",
)


def _get_client() -> Z3rnoClient:
    """Create a Z3rno SDK client from environment variables."""
    return Z3rnoClient(
        base_url=os.environ.get("Z3RNO_BASE_URL", "https://api.z3rno.dev"),
        api_key=os.environ.get("Z3RNO_API_KEY", ""),
    )


def _default_agent_id(agent_id: str | None) -> str:
    """Resolve agent_id: use the provided value or fall back to Z3RNO_AGENT_ID env var."""
    if agent_id:
        return agent_id
    env_id = os.environ.get("Z3RNO_AGENT_ID", "")
    if env_id:
        return env_id
    msg = "agent_id is required (provide it as a parameter or set Z3RNO_AGENT_ID)"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="z3rno.store",
    description=(
        "Store a memory in Z3rno. Use this to persist facts, preferences, decisions, "
        "or any information an AI agent should remember across conversations. "
        "Returns the stored memory with its ID."
    ),
)
def store(
    content: str,
    agent_id: str | None = None,
    memory_type: str = "episodic",
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    importance: float | None = None,
    ttl_seconds: int | None = None,
) -> str:
    """Store a memory in Z3rno."""
    resolved_agent_id = _default_agent_id(agent_id)
    client = _get_client()
    try:
        memory = client.store(
            agent_id=resolved_agent_id,
            content=content,
            memory_type=memory_type,
            user_id=user_id,
            metadata=metadata,
            importance=importance,
            ttl_seconds=ttl_seconds,
        )
        return json.dumps(memory.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.recall",
    description=(
        "Recall memories from Z3rno using semantic search. Use this to retrieve "
        "relevant context, past decisions, user preferences, or any previously "
        "stored information. Returns ranked results with similarity scores."
    ),
)
def recall(
    query: str,
    agent_id: str | None = None,
    memory_type: str | None = None,
    top_k: int = 10,
    similarity_threshold: float = 0.0,
    filters: dict[str, Any] | None = None,
) -> str:
    """Recall memories from Z3rno."""
    resolved_agent_id = _default_agent_id(agent_id)
    client = _get_client()
    try:
        response = client.recall(
            agent_id=resolved_agent_id,
            query=query,
            memory_type=memory_type,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
        )
        return json.dumps(response.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.forget",
    description=(
        "Forget (delete) memories from Z3rno. Supports soft delete (default) and "
        "GDPR-compliant hard delete. Use hard_delete=true for permanent, irrecoverable "
        "removal when a user exercises their right to erasure."
    ),
)
def forget(
    agent_id: str | None = None,
    memory_id: str | None = None,
    memory_ids: list[str] | None = None,
    hard_delete: bool = False,
    cascade: bool = False,
    reason: str | None = None,
) -> str:
    """Forget memories in Z3rno."""
    resolved_agent_id = _default_agent_id(agent_id)
    if not memory_id and not memory_ids:
        return json.dumps({"error": "Provide memory_id or memory_ids to delete."})
    client = _get_client()
    try:
        result = client.forget(
            agent_id=resolved_agent_id,
            memory_id=memory_id,
            memory_ids=memory_ids,
            hard_delete=hard_delete,
            cascade=cascade,
            reason=reason,
        )
        return json.dumps(result.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.audit",
    description=(
        "Query the Z3rno audit log. Returns a paginated list of operations "
        "(store, recall, forget) performed on memories. Useful for compliance, "
        "debugging, and understanding agent memory usage patterns."
    ),
)
def audit(
    agent_id: str | None = None,
    operation: str | None = None,
    memory_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """Query the Z3rno audit log."""
    client = _get_client()
    try:
        result = client.audit(
            agent_id=agent_id,
            operation=operation,
            memory_id=memory_id,
            page=page,
            page_size=page_size,
        )
        return json.dumps(result.model_dump(), default=str, indent=2)
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Z3rno MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
