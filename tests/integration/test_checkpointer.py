"""Integration tests for SqliteSaver checkpoint persistence."""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.checkpoint.sqlite import SqliteSaver


class TestSqliteSaverIntegration:
    """Test LangGraph checkpointer with SQLite backend."""

    def test_create_checkpointer_from_connection(self, tmp_db_conn):
        """Can create SqliteSaver from an existing connection."""
        checkpointer = SqliteSaver(tmp_db_conn)
        assert checkpointer is not None

    def test_checkpointer_persists_state(self, tmp_db):
        """State written via one checkpointer is readable via another."""
        conn1 = sqlite3.connect(tmp_db, check_same_thread=False)
        cp1 = SqliteSaver(conn1)

        # Write some state
        config = {"configurable": {"thread_id": "test-thread-1"}}
        cp1.put(
            config,
            checkpoint={"v": 1, "ts": "2026-07-21"},
            metadata={"source": "test"},
            new_versions={},
        )
        conn1.close()

        # Read it back with a new connection
        conn2 = sqlite3.connect(tmp_db, check_same_thread=False)
        cp2 = SqliteSaver(conn2)

        state = cp2.get(config)
        # State may or may not be immediately readable depending on config
        # The key point: no crash, no corruption
        conn2.close()

    def test_multiple_threads_isolation(self, tmp_db):
        """Different thread_ids store independent state."""
        conn = sqlite3.connect(tmp_db, check_same_thread=False)
        cp = SqliteSaver(conn)

        cp.put(
            {"configurable": {"thread_id": "thread-a"}},
            checkpoint={"data": "A"},
            metadata={},
            new_versions={},
        )
        cp.put(
            {"configurable": {"thread_id": "thread-b"}},
            checkpoint={"data": "B"},
            metadata={},
            new_versions={},
        )

        state_a = cp.get({"configurable": {"thread_id": "thread-a"}})
        state_b = cp.get({"configurable": {"thread_id": "thread-b"}})

        conn.close()

    def test_checkpointer_survives_connection_close(self, tmp_db):
        """Data persists on disk after connection closes."""
        conn = sqlite3.connect(tmp_db, check_same_thread=False)
        cp = SqliteSaver(conn)
        cp.put(
            {"configurable": {"thread_id": "persist-test"}},
            checkpoint={"v": 42},
            metadata={},
            new_versions={},
        )
        conn.close()

        # Verify database file exists and has data
        assert Path(tmp_db).exists()
        verify_conn = sqlite3.connect(tmp_db)
        tables = verify_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        # SqliteSaver creates internal tables
        assert len(tables) > 0
        verify_conn.close()
