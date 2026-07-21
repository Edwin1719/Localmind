"""Shared fixtures and mocks for Wigolo_chain tests."""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Mock wigolo client ───────────────────────────────────────────────

class MockWigoloClient:
    """Simula el cliente wigolo para tests unitarios sin daemon real."""

    def __init__(self, fail_mode: Optional[str] = None):
        self.fail_mode = fail_mode
        self.calls: list[dict[str, Any]] = []

    def search(self, **kwargs) -> dict:
        self.calls.append({"tool": "search", "params": kwargs})
        if self.fail_mode == "search":
            raise ConnectionError("mock search failure")
        return {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "excerpt": "This is a test result about " + str(kwargs.get("query", "")),
                    "citation_id": "src-1",
                    "evidence_score": {"final": 0.85},
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "excerpt": "Another test result",
                    "citation_id": "src-2",
                    "evidence_score": {"final": 0.72},
                },
            ],
            "citations": [
                {"id": "src-1", "url": "https://example.com/1"},
                {"id": "src-2", "url": "https://example.com/2"},
            ],
        }

    def fetch(self, **kwargs) -> dict:
        self.calls.append({"tool": "fetch", "params": kwargs})
        if self.fail_mode == "fetch":
            raise ConnectionError("mock fetch failure")
        url = kwargs.get("url", "")
        return {
            "url": url,
            "markdown": f"# Content from {url}\n\nThis is the extracted content.",
            "metadata": {"title": f"Page: {url}", "og_type": "article"},
            "status": "success",
        }

    def research(self, **kwargs) -> dict:
        self.calls.append({"tool": "research", "params": kwargs})
        if self.fail_mode == "research":
            raise ConnectionError("mock research failure")
        question = kwargs.get("question", "")
        return {
            "brief": {
                "topics": ["Topic A", "Topic B"],
                "highlights": ["Finding 1 about " + question, "Finding 2"],
                "key_findings": "Synthesized answer about " + question,
            },
            "sources": [{"url": "https://source1.com", "title": "Source 1"}],
            "citations": [{"id": "c1", "url": "https://source1.com"}],
        }

    def cache(self, **kwargs) -> dict:
        self.calls.append({"tool": "cache", "params": kwargs})
        if self.fail_mode == "cache":
            raise ConnectionError("mock cache failure")
        return {
            "results": [
                {
                    "url": "https://cached.example.com",
                    "title": "Cached Page",
                    "cached_at": "2026-07-21T12:00:00Z",
                }
            ],
            "total": 1,
        }

    def find_similar(self, **kwargs) -> dict:
        self.calls.append({"tool": "find_similar", "params": kwargs})
        if self.fail_mode == "find_similar":
            raise ConnectionError("mock find_similar failure")
        return {
            "results": [
                {
                    "url": "https://similar1.com",
                    "title": "Similar Page 1",
                    "match_signals": {"fused_score": 0.88},
                },
            ],
        }

    def crawl(self, **kwargs) -> dict:
        self.calls.append({"tool": "crawl", "params": kwargs})
        if self.fail_mode == "crawl":
            raise ConnectionError("mock crawl failure")
        return {
            "pages": [
                {
                    "url": "https://example.com/docs/page1",
                    "title": "Page 1",
                    "markdown": "# Page 1\n\nContent of page 1.",
                },
                {
                    "url": "https://example.com/docs/page2",
                    "title": "Page 2",
                    "markdown": "# Page 2\n\nContent of page 2.",
                },
            ],
            "total_pages": 2,
            "urls": ["https://example.com/docs/page1", "https://example.com/docs/page2"],
        }

    def extract(self, **kwargs) -> dict:
        self.calls.append({"tool": "extract", "params": kwargs})
        if self.fail_mode == "extract":
            raise ConnectionError("mock extract failure")
        return {
            "items": [
                {"name": "Item 1", "value": "Value 1"},
                {"name": "Item 2", "value": "Value 2"},
            ],
            "count": 2,
            "mode": kwargs.get("mode", "auto"),
        }

    def diff(self, **kwargs) -> dict:
        self.calls.append({"tool": "diff", "params": kwargs})
        if self.fail_mode == "diff":
            raise ConnectionError("mock diff failure")
        return {
            "hunks": [
                {
                    "type": "modified",
                    "old_text": "Python 3.12 requires Django 5.0",
                    "new_text": "Python 3.13 requires Django 5.1",
                },
                {
                    "type": "added",
                    "old_text": None,
                    "new_text": "New async ORM support added.",
                },
            ],
            "summary": "2 changes: 1 modified, 1 added",
            "granularity": kwargs.get("granularity", "section"),
        }

    def close(self):
        pass


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_wigolo():
    """Mock wigolo client that returns realistic responses."""
    return MockWigoloClient()


@pytest.fixture
def mock_wigolo_failing():
    """Mock wigolo client that fails on all tools."""
    return MockWigoloClient(fail_mode="all")


@pytest.fixture
def tmp_db():
    """Temporary SQLite database for checkpointer tests."""
    db_path = tempfile.mktemp(suffix=".db")
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def tmp_db_conn(tmp_db):
    """SQLite connection to temporary database."""
    conn = sqlite3.connect(tmp_db, check_same_thread=False)
    yield conn
    conn.close()


@pytest.fixture
def sample_search_response():
    """Sample wigolo search response for snapshot testing."""
    return {
        "results": [
            {
                "title": "Python asyncio documentation",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "excerpt": "asyncio is a library to write concurrent code...",
                "citation_id": "src-1",
                "evidence_score": {"final": 0.92, "semantic": 0.88, "lexical": 0.95},
            }
        ],
        "citations": [{"id": "src-1", "url": "https://docs.python.org/3/library/asyncio.html"}],
    }
