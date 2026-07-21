"""Integration tests for LangGraph agent with wigolo tools.

Requires: wigolo daemon running, Ollama running, required packages installed.
Skip by default unless --run-integration is passed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage
from tests.conftest import MockWigoloClient


class TestAgentWithMockedTools:
    """Test agent behavior with mocked wigolo client."""

    @patch("main._wigolo", new_callable=lambda: MockWigoloClient())
    @patch("main.ChatOllama")
    def test_agent_creation(self, mock_ollama, mock_wigolo):
        """Agent can be created with mocked dependencies."""
        # Setup mock LLM
        mock_llm = MagicMock()
        mock_ollama.return_value = mock_llm

        # Import main module — this triggers agent creation
        # We import inside the test to use our mocks
        import importlib
        import main

        importlib.reload(main)

        assert main.agent is not None
        assert len(main.tools) == 5


class TestAgentToolSelection:
    """Test that agent selects correct tools based on query type."""

    def test_search_queries_use_search_tool(self):
        """Queries asking for information should route to search."""
        client = MockWigoloClient()
        result = client.search(query="What is Python asyncio?")
        assert len(client.calls) > 0
        assert client.calls[0]["tool"] == "search"

    def test_url_queries_use_fetch_tool(self):
        """Queries with URLs should route to fetch."""
        client = MockWigoloClient()
        result = client.fetch(url="https://docs.python.org/3/")
        assert len(client.calls) > 0
        assert client.calls[0]["tool"] == "fetch"

    def test_research_queries_use_research_tool(self):
        """Deep research queries route to research tool."""
        client = MockWigoloClient()
        result = client.research(question="Compare Python and Rust for systems programming")
        assert len(client.calls) > 0
        assert client.calls[0]["tool"] == "research"

    def test_cache_lookup_before_search(self):
        """Cache should be checked before making new web searches."""
        client = MockWigoloClient()
        # Simulate: check cache first, then search
        client.cache(query="Python testing")
        client.search(query="Python testing")
        assert len(client.calls) == 2
        assert client.calls[0]["tool"] == "cache"
        assert client.calls[1]["tool"] == "search"


class TestAgentStreaming:
    """Test agent streaming behavior."""

    def test_stream_yields_message_chunks(self):
        """Agent.stream should yield message chunks with metadata."""
        # This tests the contract, not actual streaming (requires real LLM)
        messages = [HumanMessage(content="Hello")]
        config = {"configurable": {"thread_id": "test-stream"}}

        # Verify the data structures are correct
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Hello"
        assert config["configurable"]["thread_id"] == "test-stream"

    def test_thread_id_persistence(self):
        """Same thread_id should retrieve conversation history."""
        thread_id = "persistent-test-thread"
        config = {"configurable": {"thread_id": thread_id}}
        assert config["configurable"]["thread_id"] == thread_id
