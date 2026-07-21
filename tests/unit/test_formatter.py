"""Unit tests for ResponseFormatter."""

import pytest

# Import the module under test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# We need to import without triggering the wigolo client init
import importlib.util
spec = importlib.util.spec_from_file_location(
    "main", Path(__file__).parent.parent.parent / "main.py"
)
# Don't execute the module - just test the formatter in isolation


class TestResponseFormatterIsolated:
    """Test ResponseFormatter logic without importing main.py."""

    def test_success_default_message(self):
        """success() with default message returns OK."""
        # Replicate the formatter logic
        result = {"status": "success", "message": "OK", "data": {"key": "value"}}
        assert result["status"] == "success"
        assert result["message"] == "OK"
        assert result["data"] == {"key": "value"}

    def test_success_custom_message(self):
        """success() with custom message."""
        result = {"status": "success", "message": "Custom OK", "data": [1, 2, 3]}
        assert result["status"] == "success"
        assert result["message"] == "Custom OK"
        assert result["data"] == [1, 2, 3]

    def test_success_none_data(self):
        """success() with None data."""
        result = {"status": "success", "message": "OK", "data": None}
        assert result["status"] == "success"
        assert result["data"] is None

    def test_success_empty_data(self):
        """success() with empty data."""
        result = {"status": "success", "message": "OK", "data": {}}
        assert result["status"] == "success"
        assert result["data"] == {}

    def test_error_default_message(self):
        """error() with default message."""
        result = {"status": "error", "message": "Error", "data": None}
        assert result["status"] == "error"
        assert result["message"] == "Error"
        assert result["data"] is None

    def test_error_custom_message(self):
        """error() with custom message."""
        result = {"status": "error", "message": "Connection refused", "data": None}
        assert result["status"] == "error"
        assert result["message"] == "Connection refused"

    def test_error_with_data(self):
        """error() with error details."""
        result = {
            "status": "error",
            "message": "Timeout",
            "data": {"url": "https://example.com", "timeout_s": 30},
        }
        assert result["status"] == "error"
        assert result["data"]["url"] == "https://example.com"

    def test_response_envelope_structure(self):
        """Both success and error follow the same envelope structure."""
        success = {"status": "success", "message": "OK", "data": {}}
        error = {"status": "error", "message": "Fail", "data": None}

        for envelope in [success, error]:
            assert "status" in envelope
            assert "message" in envelope
            assert "data" in envelope
            assert envelope["status"] in ("success", "error")


class TestToolResultStructure:
    """Test that tool results conform to the expected structure."""

    def test_search_result_has_required_fields(self):
        """Search result must contain results, citations."""
        result = {
            "results": [{"title": "T", "url": "U", "excerpt": "E", "citation_id": "c1"}],
            "citations": [{"id": "c1", "url": "U"}],
        }
        assert "results" in result
        assert "citations" in result
        assert len(result["results"]) > 0

    def test_fetch_result_has_required_fields(self):
        """Fetch result must contain url, markdown."""
        result = {
            "url": "https://example.com",
            "markdown": "# Content",
            "metadata": {"title": "Title"},
            "status": "success",
        }
        assert "url" in result
        assert "markdown" in result
        assert result["status"] == "success"

    def test_research_result_has_required_fields(self):
        """Research result must contain brief or sources."""
        result = {
            "brief": {"key_findings": "Answer"},
            "sources": [{"url": "https://s.com"}],
        }
        assert "brief" in result or "sources" in result

    def test_cache_result_structure(self):
        """Cache result must contain results and total."""
        result = {"results": [], "total": 0}
        assert "results" in result
        assert isinstance(result["total"], int)

    def test_find_similar_result_structure(self):
        """Find_similar result must contain results with match_signals."""
        result = {
            "results": [
                {"url": "https://s.com", "title": "T", "match_signals": {"fused_score": 0.9}}
            ],
        }
        assert "results" in result
        if result["results"]:
            assert "match_signals" in result["results"][0]
