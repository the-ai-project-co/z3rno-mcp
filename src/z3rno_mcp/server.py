"""Z3rno MCP server — thin wrapper around the z3rno Python SDK + HTTP for Forge verbs.

Exposes twelve tools — the seven canonical Z3rno verbs, the viewer
helper, and four Phase G slice 2 conversation-aware tools:

  - z3rno.store                  — store a memory
  - z3rno.recall                 — semantic recall
  - z3rno.forget                 — soft or GDPR hard delete
  - z3rno.audit                  — query audit log
  - z3rno.ingest                 — accept text / URL into the Forge (Phase B.1+)
  - z3rno.distill                — build / extend the graph (Phase A)
  - z3rno.refine                 — improve the graph in place (Phase D)
  - z3rno.visualize_url          — graph-viewer URL (Phase E.5)
  - z3rno.start_conversation     — open a new session (Phase G)
  - z3rno.end_conversation       — soft-delete a session (Phase G)
  - z3rno.summarize_conversation — fetch turn history for summarization (Phase G)
  - z3rno.time_travel            — recall at a past timestamp (Phase G)

All seven verbs use the official z3rno Python SDK (v0.4.0+).
visualize_url is a deterministic URL builder; it does not call the
server.

Configuration via environment variables:
  - Z3RNO_BASE_URL  (default: https://api.z3rno.dev)
  - Z3RNO_API_KEY   (required)
  - Z3RNO_AGENT_ID  (optional default agent ID)
  - Z3RNO_WEB_URL   (default: https://app.z3rno.dev — used by visualize_url)
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP
from z3rno import Z3rnoClient

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "z3rno",
    instructions=(
        "Z3rno AI agent memory — the seven canonical verbs. "
        "store / recall / forget / audit cover day-to-day memory; "
        "ingest / distill / refine drive the Forge (graph extraction + improvement); "
        "visualize_url returns a viewer link for the current dataset."
    ),
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
# Forge tools — Phase E slice 3 additions
# ---------------------------------------------------------------------------


@mcp.tool(
    name="z3rno.ingest",
    description=(
        "Ingest text or a URL into the Z3rno Forge. Returns a job_id; the "
        "server processes the input asynchronously and (when "
        "INGEST_AUTO_DISTILL is on, which is the default) automatically "
        "chains into z3rno.distill. Use kind='text' for raw text, "
        "kind='url' for a web page. File uploads are not yet supported via MCP "
        "— use the HTTP /v1/ingest/file endpoint directly for those."
    ),
)
def ingest(
    kind: str,
    agent_id: str | None = None,
    text: str | None = None,
    url: str | None = None,
    dataset_id: str | None = None,
) -> str:
    """Ingest text or a URL into the Forge."""
    if kind not in {"text", "url"}:
        return json.dumps({"error": "kind must be 'text' or 'url'"})
    resolved_agent_id = _default_agent_id(agent_id)
    client = _get_client()
    try:
        if kind == "text":
            if not text:
                return json.dumps({"error": "kind='text' requires the 'text' parameter"})
            job = client.ingest_text(
                agent_id=resolved_agent_id, text=text, dataset_id=dataset_id
            )
        else:
            if not url:
                return json.dumps({"error": "kind='url' requires the 'url' parameter"})
            job = client.ingest_url(
                agent_id=resolved_agent_id, url=url, dataset_id=dataset_id
            )
        return json.dumps(job.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.distill",
    description=(
        "Build (or extend) the Z3rno knowledge graph from a set of stored "
        "memories. Runs the Forge pipeline: chunk → LLM entity + relationship "
        "extraction → write Memo graph nodes + edges. Returns a job_id; poll "
        "with poll_job_id=<id> on a follow-up call to read the job's state. "
        "Idempotent — re-running over already-distilled memories is a no-op."
    ),
)
def distill(
    memory_ids: list[str] | None = None,
    agent_id: str | None = None,
    poll_job_id: str | None = None,
) -> str:
    """Enqueue a Forge distillation job, or poll an existing one."""
    client = _get_client()
    try:
        if poll_job_id:
            status = client.get_distill_status(poll_job_id)
            return json.dumps(status.model_dump(), default=str, indent=2)
        if not memory_ids:
            return json.dumps(
                {"error": "provide memory_ids to distill, or poll_job_id to check status"}
            )
        resolved_agent_id = _default_agent_id(agent_id)
        job = client.distill(agent_id=resolved_agent_id, memory_ids=memory_ids)
        return json.dumps(job.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.refine",
    description=(
        "Improve the Z3rno graph in place. One refine pass does: dedupe "
        "Memos sharing an ontology URI or normalized name (SCD-2 supersede); "
        "EMA-blend edge weights from accumulated feedback; prune sub-threshold "
        "edges. Optional LLM stages (infer / summarize) are server-side flags. "
        "Returns a job_id; poll with poll_job_id=<id> to read the job's state. "
        "Admin-scoped on the server."
    ),
)
def refine(
    dataset_id: str | None = None,
    poll_job_id: str | None = None,
) -> str:
    """Enqueue a refine run, or poll an existing one."""
    client = _get_client()
    try:
        if poll_job_id:
            status = client.get_refine_status(poll_job_id)
            return json.dumps(status.model_dump(), default=str, indent=2)
        job = client.refine(dataset_id=dataset_id)
        return json.dumps(job.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.visualize_url",
    description=(
        "Return a URL to the Z3rno graph viewer for a dataset or agent. "
        "Useful when the user asks 'show me the graph' or wants to inspect "
        "the knowledge structure visually. The viewer (z3rno-web /graph) "
        "ships as part of Phase E.5; until then the returned URL may 404."
    ),
)
def visualize_url(
    dataset_id: str | None = None,
    agent_id: str | None = None,
) -> str:
    """Build a viewer URL for the current dataset / agent."""
    base = os.environ.get("Z3RNO_WEB_URL", "https://app.z3rno.dev").rstrip("/")
    params: dict[str, str] = {}
    if dataset_id:
        params["dataset_id"] = dataset_id
    if agent_id:
        params["agent_id"] = agent_id
    elif not dataset_id:
        # Neither supplied — fall back to env default if present.
        env_agent = os.environ.get("Z3RNO_AGENT_ID", "")
        if env_agent:
            params["agent_id"] = env_agent
    suffix = f"?{urlencode(params)}" if params else ""
    url = f"{base}/graph{suffix}"
    return json.dumps({"url": url}, indent=2)


# ---------------------------------------------------------------------------
# Phase G slice 2 — conversation-aware tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="z3rno.start_conversation",
    description=(
        "Open a new conversation (session). Returns the conversation id so "
        "subsequent stores can be tagged. Use this at the START of a chat "
        "with a user to enable turn-aware recall and automatic summarization."
    ),
)
def start_conversation(
    agent_id: str | None = None,
    user_id: str | None = None,
    title: str | None = None,
    summary_cadence: int = 10,
) -> str:
    """Create a Z3rno conversation row."""
    client = _get_client()
    try:
        conv = client.create_conversation(
            agent_id=_default_agent_id(agent_id),
            user_id=user_id,
            title=title,
            summary_cadence=summary_cadence,
        )
        return json.dumps(conv.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.end_conversation",
    description=(
        "Mark a conversation finished. The metadata row is soft-deleted and "
        "no further turns can be added; existing turn Memos remain intact "
        "so they can still be recalled via standard recall(). Use this when "
        "a user explicitly ends a session or the agent decides to close it."
    ),
)
def end_conversation(conversation_id: str) -> str:
    """v0.19.3 — soft-delete a conversation via the server endpoint.

    Existing turn Memos stay queryable through the standard recall
    surface; the conversation just stops accepting new turns and its
    metadata endpoints 404.
    """
    client = _get_client()
    try:
        # Snapshot final state for the response before deleting.
        try:
            conv = client.get_conversation(conversation_id)
            final_count = conv.turn_count
        except Exception:  # noqa: BLE001 — 404 / network → just delete blindly
            final_count = -1
        client.delete_conversation(conversation_id)
        return json.dumps(
            {
                "conversation_id": conversation_id,
                "turn_count": final_count,
                "status": "deleted",
            },
            indent=2,
        )
    finally:
        client.close()


@mcp.tool(
    name="z3rno.summarize_conversation",
    description=(
        "Fetch the turn history of a conversation so the agent can produce a "
        "summary. Returns turns in order with their roles + contents. The "
        "agent runs its own summarization; once done, the agent should call "
        "z3rno.store with memory_type='semantic' and metadata={'kind':'summary',"
        " 'covers_turns':[start,end]} to persist the result."
    ),
)
def summarize_conversation(
    conversation_id: str,
    after_turn: int | None = None,
    limit: int = 50,
) -> str:
    """Return the conversation's turn history for LLM summarization."""
    client = _get_client()
    try:
        page = client.list_turns(
            conversation_id, after_turn=after_turn, limit=limit
        )
        return json.dumps(page.model_dump(), default=str, indent=2)
    finally:
        client.close()


@mcp.tool(
    name="z3rno.time_travel",
    description=(
        "Recall memories as they existed at a past point in time. Uses Z3rno's "
        "SCD-2 temporal index. Supply an ISO-8601 timestamp (e.g. "
        "'2026-01-15T12:00:00Z'). Useful when the user asks 'what did I "
        "tell you last week?' or for compliance investigations."
    ),
)
def time_travel(
    as_of: str,
    query: str | None = None,
    agent_id: str | None = None,
    conversation_id: str | None = None,
    top_k: int = 10,
) -> str:
    """Recall with as_of=<timestamp> — see Phase F.3 for the temporal model."""
    from datetime import datetime

    client = _get_client()
    try:
        ts = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        resp = client.recall(
            agent_id=_default_agent_id(agent_id),
            query=query,
            top_k=top_k,
            as_of=ts,
            conversation_id=conversation_id,
        )
        return json.dumps(resp.model_dump(), default=str, indent=2)
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
