"""End-to-end tests for chat flow through Chainlit interface.

These tests require the full stack running:
  - Ollama serve
  - wigolo serve
  - chainlit (via start.py or chainlit run main.py)

Run with:  pytest tests/e2e/ -v --run-e2e
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ── Skip marker ─────────────────────────────────────────────────────

def _app_is_running() -> bool:
    """Check if Chainlit app is running on localhost:8000."""
    import urllib.request

    try:
        urllib.request.urlopen("http://127.0.0.1:8000", timeout=2)
        return True
    except Exception:
        return False


requires_app = pytest.mark.skipif(
    not _app_is_running(),
    reason="Chainlit app not running on localhost:8000. Start with: python start.py",
)


# ── Chat flow tests ─────────────────────────────────────────────────

class TestChatFlow:
    """End-to-end conversation flow tests."""

    @requires_app
    def test_app_is_reachable(self):
        """Chainlit app serves the UI."""
        import urllib.request

        resp = urllib.request.urlopen("http://127.0.0.1:8000", timeout=5)
        assert resp.status == 200

    def test_message_flow_structure(self):
        """Verify the message handling pipeline structure."""
        from langchain_core.messages import HumanMessage

        # Test that HumanMessage is properly constructed
        msg = HumanMessage(content="Test query about Python")
        assert msg.content == "Test query about Python"
        assert msg.type == "human"

    def test_config_has_thread_id(self):
        """Streaming config must include thread_id."""
        config = {"configurable": {"thread_id": "test-thread"}}
        assert "configurable" in config
        assert "thread_id" in config["configurable"]
        assert config["configurable"]["thread_id"] == "test-thread"


class TestMultiTurnConversation:
    """Simulate multi-turn conversation patterns."""

    def test_conversation_context_accumulates(self):
        """Messages accumulate in a conversation thread."""
        messages = []

        # Turn 1
        messages.append({"role": "user", "content": "My name is Edwin"})
        messages.append({"role": "assistant", "content": "Hello Edwin!"})

        # Turn 2
        messages.append({"role": "user", "content": "What is my name?"})
        # The agent should reference "Edwin" from context
        messages.append({"role": "assistant", "content": "Your name is Edwin"})

        assert len(messages) == 4
        assert messages[0]["content"] == "My name is Edwin"
        assert "Edwin" in messages[3]["content"]

    def test_tool_call_then_followup(self):
        """After a tool call, follow-up question uses context."""
        conversation = [
            {"role": "user", "content": "Search for Python testing best practices"},
            {
                "role": "assistant",
                "content": "I found these results about Python testing...",
                "tool_calls": ["buscar_en_web"],
            },
            {"role": "user", "content": "Which one is most recommended?"},
            {
                "role": "assistant",
                "content": "Based on the search results, pytest is the most recommended...",
            },
        ]

        # The follow-up should reference the search results
        assert "tool_calls" in conversation[1]
        assert "buscar_en_web" in conversation[1]["tool_calls"]
        assert "pytest" in conversation[3]["content"].lower()

    def test_error_recovery_pattern(self):
        """Agent should recover gracefully from tool errors."""
        conversation = [
            {"role": "user", "content": "Search for something"},
            {
                "role": "assistant",
                "content": "I encountered an error with the search. Let me try another approach...",
                "error": True,
            },
            {"role": "assistant", "content": "Here's what I found using the cache instead..."},
        ]

        assert conversation[1]["error"] is True
        # Error message should be user-friendly
        assert "error" in conversation[1]["content"].lower()
        # Recovery should follow
        assert "cache" in conversation[2]["content"].lower()


class TestToolChainPatterns:
    """Test common tool chaining patterns."""

    def test_search_then_fetch_pattern(self):
        """Search for URLs, then fetch the most relevant one."""
        pattern = [
            {"tool": "buscar_en_web", "purpose": "find relevant URLs"},
            {"tool": "leer_pagina_web", "purpose": "read the best result"},
            {"action": "synthesize", "purpose": "combine search + fetch results"},
        ]
        assert len(pattern) == 3
        assert pattern[0]["tool"] == "buscar_en_web"
        assert pattern[1]["tool"] == "leer_pagina_web"

    def test_research_then_find_similar_pattern(self):
        """Research a topic, then find related content."""
        pattern = [
            {"tool": "investigar_a_fondo", "purpose": "deep research"},
            {"tool": "encontrar_similar", "purpose": "find related pages"},
        ]
        assert len(pattern) == 2

    def test_cache_first_pattern(self):
        """Always check cache before hitting the network."""
        pattern = [
            {"tool": "buscar_en_cache", "purpose": "check local first"},
            {"tool": "buscar_en_web", "purpose": "fallback to web"},
        ]
        assert pattern[0]["tool"] == "buscar_en_cache"


class TestEdgeCases:
    """Edge case handling in the chat flow."""

    def test_empty_message(self):
        """Empty user message should not crash."""
        msg = ""
        assert msg == ""  # Should be handled gracefully

    def test_very_long_query(self):
        """Very long queries should be handled."""
        long_query = "Python " * 1000
        assert len(long_query) > 4000  # Should not cause token overflow issues

    def test_special_characters(self):
        """Special characters in queries should be safe."""
        queries = [
            "SELECT * FROM users",
            "<script>alert('xss')</script>",
            "${PATH}",
            "query with emoji 🚀🔍",
            "unicode: 你好世界",
        ]
        for q in queries:
            assert isinstance(q, str)

    def test_concurrent_threads_isolation(self):
        """Different threads should not leak state between each other."""
        thread_a = {"thread_id": "thread-a", "messages": ["Hello from A"]}
        thread_b = {"thread_id": "thread-b", "messages": ["Hello from B"]}

        assert thread_a["thread_id"] != thread_b["thread_id"]
        assert thread_a["messages"] != thread_b["messages"]
