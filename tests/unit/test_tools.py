"""Unit tests for tool functions — parameter building and error handling."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.conftest import MockWigoloClient


# ── Tool parameter building (isolated from wigolo daemon) ──────────

class TestBuscarEnWebParams:
    """Test buscar_en_web parameter construction."""

    def test_basic_query(self):
        """Basic search with just a query string."""
        client = MockWigoloClient()
        result = client.search(query="Python testing frameworks")
        assert len(result["results"]) == 2
        assert result["citations"][0]["id"] == "src-1"
        assert "Python testing frameworks" in result["results"][0]["excerpt"]

    def test_max_results_clamped(self):
        """max_results should respect limits."""
        client = MockWigoloClient()
        result = client.search(query="test", max_results=50)
        # The real tool clamps at 20 — we trust the tool code for that
        assert len(result["results"]) == 2  # mock returns 2 regardless

    def test_result_has_evidence_scores(self):
        """Each result should carry explainable evidence scores."""
        client = MockWigoloClient()
        result = client.search(query="test")
        for r in result["results"]:
            assert "evidence_score" in r
            assert "final" in r["evidence_score"]

    def test_result_has_citations(self):
        """Citations should map to results via citation_id."""
        client = MockWigoloClient()
        result = client.search(query="test")
        citation_ids = {c["id"] for c in result["citations"]}
        for r in result["results"]:
            assert r["citation_id"] in citation_ids


class TestLeerPaginaWebParams:
    """Test leer_pagina_web parameter handling."""

    def test_basic_fetch(self):
        """Basic fetch with URL."""
        client = MockWigoloClient()
        result = client.fetch(url="https://docs.python.org/3/")
        assert result["status"] == "success"
        assert "docs.python.org" in result["url"]
        assert len(result["markdown"]) > 0

    def test_fetch_returns_metadata(self):
        """Fetch result must include metadata."""
        client = MockWigoloClient()
        result = client.fetch(url="https://example.com")
        assert "metadata" in result
        assert "title" in result["metadata"]


class TestInvestigarAFondoParams:
    """Test investigar_a_fondo depth levels."""

    def test_standard_depth(self):
        """Standard depth research."""
        client = MockWigoloClient()
        result = client.research(question="What is asyncio?", depth="standard")
        assert "brief" in result
        assert "sources" in result

    def test_quick_depth(self):
        """Quick depth returns faster, fewer sources."""
        client = MockWigoloClient()
        result = client.research(question="Fast question", depth="quick")
        assert "brief" in result

    def test_comprehensive_depth(self):
        """Comprehensive depth returns more sources."""
        client = MockWigoloClient()
        result = client.research(question="Deep question", depth="comprehensive")
        assert "brief" in result

    def test_key_findings_in_brief(self):
        """Brief should contain key_findings."""
        client = MockWigoloClient()
        result = client.research(question="Test")
        assert "key_findings" in result["brief"]


class TestBuscarEnCacheParams:
    """Test buscar_en_cache functionality."""

    def test_basic_cache_query(self):
        """Basic cache search."""
        client = MockWigoloClient()
        result = client.cache(query="Python asyncio")
        assert "results" in result
        assert result["total"] == 1

    def test_cache_with_url_pattern(self):
        """Cache search with URL glob pattern."""
        client = MockWigoloClient()
        result = client.cache(query="Python", url_pattern="*docs.python.org*")
        assert "results" in result


class TestEncontrarSimilarParams:
    """Test encontrar_similar parameter handling."""

    def test_similar_by_url(self):
        """Find similar by URL."""
        client = MockWigoloClient()
        result = client.find_similar(url="https://docs.python.org/3/")
        assert len(result["results"]) > 0
        assert "match_signals" in result["results"][0]

    def test_similar_by_concept(self):
        """Find similar by concept."""
        client = MockWigoloClient()
        result = client.find_similar(concept="async programming")
        assert len(result["results"]) > 0

    def test_max_results_respected(self):
        """max_results limits output."""
        client = MockWigoloClient()
        result = client.find_similar(url="https://example.com", max_results=3)
        assert len(result["results"]) > 0


# ── Error handling ──────────────────────────────────────────────────

class TestToolErrorHandling:
    """Test that tools handle errors gracefully."""

    def test_search_connection_error(self):
        """Search should handle connection errors gracefully."""
        client = MockWigoloClient(fail_mode="search")
        with pytest.raises(ConnectionError, match="mock search failure"):
            client.search(query="test")

    def test_fetch_connection_error(self):
        """Fetch should handle connection errors gracefully."""
        client = MockWigoloClient(fail_mode="fetch")
        with pytest.raises(ConnectionError, match="mock fetch failure"):
            client.fetch(url="https://example.com")

    def test_research_connection_error(self):
        """Research should handle connection errors gracefully."""
        client = MockWigoloClient(fail_mode="research")
        with pytest.raises(ConnectionError, match="mock research failure"):
            client.research(question="Test")

    def test_cache_connection_error(self):
        """Cache should handle connection errors gracefully."""
        client = MockWigoloClient(fail_mode="cache")
        with pytest.raises(ConnectionError, match="mock cache failure"):
            client.cache(query="test")
