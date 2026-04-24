"""SQLite-backed cache storage helpers.

This module provides a minimal standard-library sqlite3 adapter that can be
used incrementally by Venus components while preserving current behavior.
"""
import os
import sqlite3
import time

from . import config


def database_path():
    """Return the absolute path of the cache SQLite database file."""
    return os.path.join(config.cache_directory(), "cache.sqlite3")


def connect(create=True):
    """Open a SQLite connection and ensure the minimal schema exists."""
    path = database_path()
    if not create and not os.path.exists(path):
        return None

    os.makedirs(config.cache_directory(), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    return conn


def ensure_schema(conn):
    """Create the cache schema if it does not already exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feeds (
            feed_uri TEXT PRIMARY KEY,
            feed_id TEXT,
            source_xml TEXT,
            updated_ts INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS entries (
            entry_key TEXT PRIMARY KEY,
            entry_id TEXT,
            feed_id TEXT,
            updated_ts INTEGER NOT NULL DEFAULT 0,
            entry_xml TEXT,
            blacklisted INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reading_lists (
            list_uri TEXT PRIMARY KEY,
            etag TEXT,
            last_modified TEXT,
            payload TEXT,
            updated_ts INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS id_index (
            entry_key TEXT PRIMARY KEY,
            feed_id TEXT NOT NULL,
            updated_ts INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()


class IdIndexStore:
    """Dictionary-like facade backed by the SQLite `id_index` table."""

    def __init__(self, conn):
        self._conn = conn

    def __len__(self):
        row = self._conn.execute("SELECT COUNT(*) FROM id_index").fetchone()
        return row[0] if row else 0

    def __getitem__(self, key):
        row = self._conn.execute(
            "SELECT feed_id FROM id_index WHERE entry_key = ?", (key,)
        ).fetchone()
        if not row:
            raise KeyError(key)
        return row[0]

    def __setitem__(self, key, value):
        self._conn.execute(
            """
            INSERT INTO id_index(entry_key, feed_id, updated_ts)
            VALUES(?, ?, ?)
            ON CONFLICT(entry_key)
            DO UPDATE SET feed_id = excluded.feed_id, updated_ts = excluded.updated_ts
            """,
            (key, value, int(time.time())),
        )
        self._conn.commit()

    def __contains__(self, key):
        row = self._conn.execute(
            "SELECT 1 FROM id_index WHERE entry_key = ? LIMIT 1", (key,)
        ).fetchone()
        return row is not None

    def keys(self):
        rows = self._conn.execute("SELECT entry_key FROM id_index").fetchall()
        return [row[0] for row in rows]

    def clear(self):
        self._conn.execute("DELETE FROM id_index")
        self._conn.commit()

    def close(self):
        self._conn.close()


def open_id_index(create=False):
    """Open the id-index facade, optionally creating the database."""
    conn = connect(create=create)
    if conn is None:
        return None
    return IdIndexStore(conn)


def clear_id_index():
    """Remove all id-index rows while keeping the database and schema."""
    conn = connect(create=False)
    if conn is None:
        return
    conn.execute("DELETE FROM id_index")
    conn.commit()
    conn.close()


def upsert_feed(feed_uri, feed_id, source_xml, updated_ts=None):
    """Insert or update cached feed metadata."""
    conn = connect(create=True)
    conn.execute(
        """
        INSERT INTO feeds(feed_uri, feed_id, source_xml, updated_ts)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(feed_uri)
        DO UPDATE SET
            feed_id = excluded.feed_id,
            source_xml = excluded.source_xml,
            updated_ts = excluded.updated_ts
        """,
        (feed_uri, feed_id, source_xml, int(updated_ts or time.time())),
    )
    conn.commit()
    conn.close()


def upsert_entry(entry_key, entry_id, feed_id, updated_ts, entry_xml, blacklisted=0):
    """Insert or update one cached entry row."""
    conn = connect(create=True)
    conn.execute(
        """
        INSERT INTO entries(entry_key, entry_id, feed_id, updated_ts, entry_xml, blacklisted)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(entry_key)
        DO UPDATE SET
            entry_id = excluded.entry_id,
            feed_id = excluded.feed_id,
            updated_ts = excluded.updated_ts,
            entry_xml = excluded.entry_xml,
            blacklisted = excluded.blacklisted
        """,
        (entry_key, entry_id, feed_id, int(updated_ts), entry_xml, int(bool(blacklisted))),
    )
    conn.commit()
    conn.close()


def delete_entry(entry_key):
    """Delete one cached entry by key."""
    conn = connect(create=False)
    if conn is None:
        return
    conn.execute("DELETE FROM entries WHERE entry_key = ?", (entry_key,))
    conn.commit()
    conn.close()


def mark_entry_blacklisted(entry_key, blacklisted=True):
    """Mark an existing cached entry as blacklisted/unblacklisted."""
    conn = connect(create=False)
    if conn is None:
        return
    conn.execute(
        "UPDATE entries SET blacklisted = ? WHERE entry_key = ?",
        (int(bool(blacklisted)), entry_key),
    )
    conn.commit()
    conn.close()


def list_entries_by_recency():
    """Return cached entries ordered from newest to oldest."""
    conn = connect(create=False)
    if conn is None:
        return []
    rows = conn.execute(
        """
        SELECT entry_key, entry_id, feed_id, updated_ts, entry_xml, blacklisted
        FROM entries
        ORDER BY updated_ts DESC, entry_key DESC
        """
    ).fetchall()
    conn.close()
    return rows


def entries_count():
    """Return total number of cached entry rows."""
    conn = connect(create=False)
    if conn is None:
        return 0
    row = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
    conn.close()
    return row[0] if row else 0


def destroy_database():
    """Remove the SQLite cache database file if it exists."""
    path = database_path()
    if os.path.exists(path):
        os.unlink(path)
