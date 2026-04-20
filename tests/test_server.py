"""Tests for z3rno-mcp server tool registration and handler logic.

Tests the tool definitions and handler functions with a mocked Z3rnoClient.
Does NOT test actual MCP transport.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from z3rno_mcp.server import mcp, store, recall, forget, audit


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {"z3rno.store", "z3rno.recall", "z3rno.forget", "z3rno.audit"}


class TestToolRegistration:
    """Verify the FastMCP instance has all four tools registered."""

    def test_all_tools_registered(self):
        tools = mcp.list_tools()
        registered_names = {t.name for t in tools}
        assert EXPECTED_TOOLS == registered_names, (
            f"Expected tools {EXPECTED_TOOLS}, got {registered_names}"
        )

    def test_no_extra_tools(self):
        tools = mcp.list_tools()
        registered_names = {t.name for t in tools}
        assert len(registered_names) == len(EXPECTED_TOOLS)


# ---------------------------------------------------------------------------
# Tool input schemas
# ---------------------------------------------------------------------------


class TestToolSchemas:
    """Verify tool input schemas are well-formed."""

    @pytest.fixture()
    def tool_map(self):
        return {t.name: t for t in mcp.list_tools()}

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
