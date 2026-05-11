"""Tests for z3rno-mcp server tool registration and handler logic.

Tests the tool definitions and handler functions with a mocked Z3rnoClient
(for SDK-backed tools) and a mocked httpx layer (for Forge tools). Does
NOT test actual MCP transport.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from z3rno_mcp.server import (
    audit,
    distill,
    forget,
    ingest,
    mcp,
    recall,
    refine,
    store,
    visualize_url,
)

# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "z3rno.store",
    "z3rno.recall",
    "z3rno.forget",
    "z3rno.audit",
    "z3rno.ingest",
    "z3rno.distill",
    "z3rno.refine",
    "z3rno.visualize_url",
}


def _registered_tools():
    """Sync wrapper around the async mcp.list_tools()."""
    return asyncio.run(mcp.list_tools())


class TestToolRegistration:
    """Verify the FastMCP instance has all eight tools registered."""

    def test_all_tools_registered(self):
        tools = _registered_tools()
        registered_names = {t.name for t in tools}
        assert registered_names == EXPECTED_TOOLS, (
            f"Expected tools {EXPECTED_TOOLS}, got {registered_names}"
        )

    def test_no_extra_tools(self):
        tools = _registered_tools()
        registered_names = {t.name for t in tools}
        assert len(registered_names) == len(EXPECTED_TOOLS)


# ---------------------------------------------------------------------------
# Tool input schemas
# ---------------------------------------------------------------------------


class TestToolSchemas:
    """Verify tool input schemas are well-formed."""

    @pytest.fixture()
    def tool_map(self):
        return {t.name: t for t in _registered_tools()}

    def test_store_schema_has_content(self, tool_map):
        schema = tool_map["z3rno.store"].inputSchema
        assert "content" in schema.get("properties", {}), "store should require 'content'"

    def test_recall_schema_has_query(self, tool_map):
        schema = tool_map["z3rno.recall"].inputSchema
        assert "query" in schema.get("properties", {}), "recall should require 'query'"

    def test_forget_schema_has_memory_id(self, tool_map):
        schema = tool_map["z3rno.forget"].inputSchema
        props = schema.get("properties", {})
        assert "memory_id" in props or "memory_ids" in props, (
            "forget should accept memory_id or memory_ids"
        )

    def test_audit_schema_has_page(self, tool_map):
        schema = tool_map["z3rno.audit"].inputSchema
        assert "page" in schema.get("properties", {}), "audit should accept 'page'"

    def test_all_schemas_are_objects(self, tool_map):
        for name, tool in tool_map.items():
            schema = tool.inputSchema
            assert schema.get("type") == "object", f"{name} schema type should be 'object'"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_memory(**overrides):
    """Return a MagicMock that behaves like a Z3rno Memory model."""
    defaults = {
        "id": "mem_abc123",
        "agent_id": "test-agent",
        "content": "test content",
        "memory_type": "episodic",
        "importance": 0.5,
        "created_at": "2026-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    m = MagicMock()
    m.model_dump.return_value = defaults
    return m


def _mock_recall_response(memories=None):
    m = MagicMock()
    m.model_dump.return_value = {
        "memories": memories or [],
        "total": len(memories or []),
    }
    return m


def _mock_result(**overrides):
    defaults = {"deleted": 1, "hard_deleted": False}
    defaults.update(overrides)
    m = MagicMock()
    m.model_dump.return_value = defaults
    return m


def _mock_audit_response(entries=None):
    m = MagicMock()
    m.model_dump.return_value = {
        "entries": entries or [],
        "page": 1,
        "page_size": 50,
        "total": len(entries or []),
    }
    return m


# ---------------------------------------------------------------------------
# Tool handler tests
# ---------------------------------------------------------------------------


class TestStoreHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_store_returns_json(self, mock_get_client):
        client = MagicMock()
        client.store.return_value = _mock_memory(content="user likes dark mode")
        mock_get_client.return_value = client

        result = store(content="user likes dark mode", agent_id="test-agent")
        parsed = json.loads(result)

        assert parsed["content"] == "user likes dark mode"
        assert parsed["id"] == "mem_abc123"
        client.store.assert_called_once()
        client.close.assert_called_once()

    @patch("z3rno_mcp.server._get_client")
    def test_store_passes_optional_fields(self, mock_get_client):
        client = MagicMock()
        client.store.return_value = _mock_memory()
        mock_get_client.return_value = client

        store(
            content="test",
            agent_id="a",
            memory_type="semantic",
            importance=0.9,
            ttl_seconds=3600,
            metadata={"source": "test"},
        )

        call_kwargs = client.store.call_args.kwargs
        assert call_kwargs["memory_type"] == "semantic"
        assert call_kwargs["importance"] == 0.9
        assert call_kwargs["ttl_seconds"] == 3600


class TestRecallHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_recall_returns_json(self, mock_get_client):
        client = MagicMock()
        client.recall.return_value = _mock_recall_response(
            memories=[{"id": "mem_1", "content": "hello", "score": 0.95}]
        )
        mock_get_client.return_value = client

        result = recall(query="hello", agent_id="test-agent")
        parsed = json.loads(result)

        assert parsed["total"] == 1
        assert len(parsed["memories"]) == 1
        client.recall.assert_called_once()
        client.close.assert_called_once()


class TestForgetHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_forget_single_memory(self, mock_get_client):
        client = MagicMock()
        client.forget.return_value = _mock_result(deleted=1)
        mock_get_client.return_value = client

        result = forget(memory_id="mem_abc123", agent_id="test-agent")
        parsed = json.loads(result)

        assert parsed["deleted"] == 1
        client.forget.assert_called_once()
        client.close.assert_called_once()

    def test_forget_requires_memory_id_or_ids(self):
        result = forget(agent_id="test-agent")
        parsed = json.loads(result)
        assert "error" in parsed


class TestAuditHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_audit_returns_json(self, mock_get_client):
        client = MagicMock()
        client.audit.return_value = _mock_audit_response(
            entries=[{"operation": "store", "memory_id": "mem_1"}]
        )
        mock_get_client.return_value = client

        result = audit(agent_id="test-agent")
        parsed = json.loads(result)

        assert parsed["total"] == 1
        client.audit.assert_called_once()
        client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Agent ID resolution
# ---------------------------------------------------------------------------


class TestAgentIdResolution:
    @patch("z3rno_mcp.server._get_client")
    @patch.dict("os.environ", {"Z3RNO_AGENT_ID": "env-agent"})
    def test_falls_back_to_env_agent_id(self, mock_get_client):
        client = MagicMock()
        client.store.return_value = _mock_memory()
        mock_get_client.return_value = client

        store(content="test")

        call_kwargs = client.store.call_args.kwargs
        assert call_kwargs["agent_id"] == "env-agent"

    @patch("z3rno_mcp.server._get_client")
    def test_raises_without_agent_id(self, mock_get_client):
        with pytest.raises(ValueError, match="agent_id is required"):
            store(content="test")




# ---------------------------------------------------------------------------
# Forge tools — Phase E slice 3, refactored to use SDK methods (v0.4.0+)
# ---------------------------------------------------------------------------


def _mock_job(**overrides):
    """Stand-in for an IngestJob/DistillJob/RefineJob SDK model."""
    defaults = {
        "job_id": "j-1",
        "status": "queued",
        "kind": "text",
        "memory_ids": [],
        "enqueued_at": "2026-05-11T00:00:00Z",
    }
    defaults.update(overrides)
    m = MagicMock()
    m.model_dump.return_value = defaults
    return m


class TestIngestHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_ingest_text_calls_sdk(self, mock_get_client):
        client = MagicMock()
        client.ingest_text.return_value = _mock_job(job_id="ij-1", kind="text")
        mock_get_client.return_value = client

        result = ingest(kind="text", agent_id="a1", text="hello world")
        parsed = json.loads(result)
        assert parsed["job_id"] == "ij-1"
        client.ingest_text.assert_called_once_with(
            agent_id="a1", text="hello world", dataset_id=None
        )
        client.close.assert_called_once()

    @patch("z3rno_mcp.server._get_client")
    def test_ingest_url_calls_sdk(self, mock_get_client):
        client = MagicMock()
        client.ingest_url.return_value = _mock_job(job_id="ij-2", kind="url")
        mock_get_client.return_value = client

        ingest(kind="url", agent_id="a1", url="https://example.com")
        client.ingest_url.assert_called_once_with(
            agent_id="a1", url="https://example.com", dataset_id=None
        )

    @patch("z3rno_mcp.server._get_client")
    def test_ingest_dataset_id_threaded(self, mock_get_client):
        client = MagicMock()
        client.ingest_text.return_value = _mock_job()
        mock_get_client.return_value = client

        ingest(kind="text", agent_id="a1", text="x", dataset_id="ds-1")
        assert client.ingest_text.call_args.kwargs["dataset_id"] == "ds-1"

    def test_ingest_rejects_unknown_kind(self):
        parsed = json.loads(ingest(kind="bogus", agent_id="a1"))
        assert "error" in parsed

    def test_ingest_text_without_text_errors(self):
        parsed = json.loads(ingest(kind="text", agent_id="a1"))
        assert "error" in parsed

    def test_ingest_url_without_url_errors(self):
        parsed = json.loads(ingest(kind="url", agent_id="a1"))
        assert "error" in parsed


class TestDistillHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_distill_enqueue(self, mock_get_client):
        client = MagicMock()
        client.distill.return_value = _mock_job(job_id="dj-1")
        mock_get_client.return_value = client

        result = distill(memory_ids=["m1", "m2"], agent_id="a1")
        assert json.loads(result)["job_id"] == "dj-1"
        client.distill.assert_called_once_with(
            agent_id="a1", memory_ids=["m1", "m2"]
        )

    @patch("z3rno_mcp.server._get_client")
    def test_distill_poll(self, mock_get_client):
        client = MagicMock()
        client.get_distill_status.return_value = _mock_job(
            job_id="dj-1", status="completed"
        )
        mock_get_client.return_value = client

        distill(poll_job_id="dj-1")
        client.get_distill_status.assert_called_once_with("dj-1")
        client.distill.assert_not_called()

    @patch("z3rno_mcp.server._get_client")
    def test_distill_without_inputs_errors(self, mock_get_client):
        client = MagicMock()
        mock_get_client.return_value = client

        parsed = json.loads(distill(agent_id="a1"))
        assert "error" in parsed
        client.distill.assert_not_called()


class TestRefineHandler:
    @patch("z3rno_mcp.server._get_client")
    def test_refine_enqueue_without_dataset(self, mock_get_client):
        client = MagicMock()
        client.refine.return_value = _mock_job(job_id="rj-1")
        mock_get_client.return_value = client

        refine()
        client.refine.assert_called_once_with(dataset_id=None)

    @patch("z3rno_mcp.server._get_client")
    def test_refine_enqueue_with_dataset(self, mock_get_client):
        client = MagicMock()
        client.refine.return_value = _mock_job(job_id="rj-2")
        mock_get_client.return_value = client

        refine(dataset_id="ds-1")
        client.refine.assert_called_once_with(dataset_id="ds-1")

    @patch("z3rno_mcp.server._get_client")
    def test_refine_poll(self, mock_get_client):
        client = MagicMock()
        client.get_refine_status.return_value = _mock_job(
            job_id="rj-9", status="running"
        )
        mock_get_client.return_value = client

        refine(poll_job_id="rj-9")
        client.get_refine_status.assert_called_once_with("rj-9")
        client.refine.assert_not_called()


class TestVisualizeUrlHandler:
    def test_default_url_uses_env(self, monkeypatch):
        monkeypatch.setenv("Z3RNO_WEB_URL", "https://example.dev")
        parsed = json.loads(visualize_url(dataset_id="ds-1"))
        assert parsed["url"] == "https://example.dev/graph?dataset_id=ds-1"

    def test_agent_id_param(self, monkeypatch):
        monkeypatch.setenv("Z3RNO_WEB_URL", "https://x.dev")
        parsed = json.loads(visualize_url(agent_id="a-1"))
        assert parsed["url"] == "https://x.dev/graph?agent_id=a-1"

    def test_both_params(self, monkeypatch):
        monkeypatch.setenv("Z3RNO_WEB_URL", "https://x.dev")
        parsed = json.loads(visualize_url(dataset_id="ds-1", agent_id="a-1"))
        assert "dataset_id=ds-1" in parsed["url"]
        assert "agent_id=a-1" in parsed["url"]

    def test_neither_param_falls_back_to_env_agent(self, monkeypatch):
        monkeypatch.setenv("Z3RNO_WEB_URL", "https://x.dev")
        monkeypatch.setenv("Z3RNO_AGENT_ID", "env-agent")
        parsed = json.loads(visualize_url())
        assert parsed["url"] == "https://x.dev/graph?agent_id=env-agent"

    def test_neither_and_no_env_returns_bare_url(self, monkeypatch):
        monkeypatch.setenv("Z3RNO_WEB_URL", "https://x.dev")
        monkeypatch.delenv("Z3RNO_AGENT_ID", raising=False)
        parsed = json.loads(visualize_url())
        assert parsed["url"] == "https://x.dev/graph"

    def test_default_web_url_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("Z3RNO_WEB_URL", raising=False)
        monkeypatch.delenv("Z3RNO_AGENT_ID", raising=False)
        parsed = json.loads(visualize_url())
        assert parsed["url"] == "https://app.z3rno.dev/graph"
