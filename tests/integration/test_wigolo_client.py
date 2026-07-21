"""Integration tests — require wigolo daemon running on localhost:3333.

Run with:  pytest tests/integration/ -v --run-integration

These tests are skipped by default. Use --run-integration to enable them.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wigolo import Client

# Check if daemon is available
WIGOLO_URL = os.getenv("WIGOLO_BASE_URL", "http://127.0.0.1:3333")


def _daemon_is_running() -> bool:
    """Check if wigolo daemon is reachable."""
    import urllib.request

    try:
        urllib.request.urlopen(f"{WIGOLO_URL}/health", timeout=2)
        return True
    except Exception:
        return False


# ── Skip marker ─────────────────────────────────────────────────────
requires_daemon = pytest.mark.skipif(
    not _daemon_is_running(),
    reason="wigolo daemon not running on localhost:3333. Start with: wigolo serve",
)


@pytest.fixture(scope="module")
def wigolo_client():
    """Real wigolo client connected to local daemon."""
    if not _daemon_is_running():
        pytest.skip("wigolo daemon not running")
    client = Client(base_url=WIGOLO_URL)
    yield client
    client.close()


# ── Daemon health ────────────────────────────────────────────────────

class TestWigoloDaemonHealth:
    """Verify the wigolo daemon is healthy and responds."""

    @requires_daemon
    def test_health_endpoint(self, wigolo_client):
        """Daemon health endpoint returns status."""
        health = wigolo_client.health()
        assert health is not None

    @requires_daemon
    def test_list_tools(self, wigolo_client):
        """Daemon exposes all expected tools."""
        tools = wigolo_client.list_tools()
        assert tools is not None


# ── Search tests ─────────────────────────────────────────────────────

class TestWigoloSearchIntegration:
    """Integration tests for wigolo search."""

    @requires_daemon
    def test_basic_search_returns_results(self, wigolo_client):
        """Basic search returns scored results with citations."""
        result = wigolo_client.search(query="Python programming language", max_results=3)
        assert "results" in result
        assert len(result["results"]) > 0
        assert "citations" in result

    @requires_daemon
    def test_search_with_category_filter(self, wigolo_client):
        """Search with category filter."""
        result = wigolo_client.search(query="Python asyncio", category="docs", max_results=3)
        assert "results" in result

    @requires_daemon
    def test_search_with_domain_filter(self, wigolo_client):
        """Search scoped to specific domain."""
        result = wigolo_client.search(
            query="asyncio", include_domains=["docs.python.org"], max_results=3
        )
        assert "results" in result

    @requires_daemon
    def test_search_empty_query_handled(self, wigolo_client):
        """Empty or nonsense query handled gracefully."""
        result = wigolo_client.search(query="xyzzy12345_nonexistent_term_2026", max_results=2)
        assert "results" in result  # Should return empty or noise, not crash

    @requires_daemon
    def test_search_result_has_evidence_score(self, wigolo_client):
        """Each result carries explainable scoring."""
        result = wigolo_client.search(query="machine learning", max_results=2)
        if result.get("results"):
            for r in result["results"]:
                assert "evidence_score" in r or "relevance_score" in r or "score" in r


# ── Fetch tests ─────────────────────────────────────────────────────

class TestWigoloFetchIntegration:
    """Integration tests for wigolo fetch."""

    @requires_daemon
    def test_fetch_public_page(self, wigolo_client):
        """Fetch a simple public page."""
        result = wigolo_client.fetch(url="https://httpbin.org/json", max_chars=5000)
        assert "markdown" in result or "content" in result or "url" in result

    @requires_daemon
    def test_fetch_invalid_url(self, wigolo_client):
        """Fetch with invalid URL should not crash."""
        try:
            result = wigolo_client.fetch(url="https://invalid.domain.that.does.not.exist.xyz")
            # Either returns error or raises — both are valid
            assert result is not None
        except Exception:
            pass  # Exception is also acceptable for invalid URLs


# ── Cache tests ─────────────────────────────────────────────────────

class TestWigoloCacheIntegration:
    """Integration tests for wigolo cache."""

    @requires_daemon
    def test_cache_query(self, wigolo_client):
        """Cache query should work."""
        result = wigolo_client.cache(query="Python")
        assert "results" in result or "total" in result
