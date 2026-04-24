#!/usr/bin/env python

import os
import shutil
import sqlite3
import unittest

from planet import config, storage


WORKDIR = "tests/work/storage/cache"
CONFIGFILE = "tests/data/storage/config.ini"


class StorageTest(unittest.TestCase):
    def setUp(self):
        config.load(CONFIGFILE)

    def tearDown(self):
        if os.path.exists(WORKDIR):
            shutil.rmtree(WORKDIR)
            os.removedirs(os.path.split(WORKDIR)[0])

    def test_open_id_index_returns_none_without_database(self):
        self.assertIsNone(storage.open_id_index(create=False))

    def test_schema_and_id_index_crud(self):
        conn = storage.connect(create=True)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertTrue("id_index" in tables)
            self.assertTrue("entries" in tables)
            self.assertTrue("feeds" in tables)
            self.assertTrue("reading_lists" in tables)
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(entries)").fetchall()
            }
            self.assertEqual(
                set(["entry_key", "entry_id", "feed_id", "updated_ts", "entry_xml"]),
                columns,
            )
        finally:
            conn.close()

        index = storage.open_id_index(create=False)
        self.assertEqual(0, len(index))
        index["one"] = "feed:a"
        index["two"] = "feed:b"
        index["one"] = "feed:c"

        self.assertEqual(2, len(index))
        self.assertTrue("one" in index)
        self.assertEqual("feed:c", index["one"])
        self.assertEqual(set(["one", "two"]), set(index.keys()))
        index.close()

        with self.assertRaises(sqlite3.ProgrammingError):
            index.keys()

    def test_database_path_and_destroy_database(self):
        self.assertEqual(
            os.path.join(WORKDIR, "cache.sqlite3"),
            storage.database_path(),
        )

        storage.connect(create=True).close()
        self.assertTrue(os.path.exists(storage.database_path()))

        storage.destroy_database()
        self.assertFalse(os.path.exists(storage.database_path()))

        storage.destroy_database()
        self.assertFalse(os.path.exists(storage.database_path()))

    def test_feed_and_entry_crud_helpers(self):
        storage.upsert_feed("feed:one", "id:one", "<feed>one</feed>", updated_ts=100)
        storage.upsert_feed("feed:one", "id:two", "<feed>two</feed>", updated_ts=200)

        conn = storage.connect(create=False)
        try:
            row = conn.execute(
                "SELECT feed_id, source_xml, updated_ts FROM feeds WHERE feed_uri = ?",
                ("feed:one",),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(("id:two", "<feed>two</feed>", 200), row)

        self.assertEqual(0, storage.entries_count())
        storage.upsert_entry("entry:b", "id:b", "feed:one", 20, "<entry>b</entry>")
        storage.upsert_entry("entry:a", "id:a", "feed:one", 10, "<entry>a</entry>")
        storage.upsert_entry("entry:a", "id:a2", "feed:two", 30, "<entry>a2</entry>")

        self.assertEqual(2, storage.entries_count())
        self.assertEqual(
            [
                ("entry:a", "id:a2", "feed:two", 30, "<entry>a2</entry>"),
                ("entry:b", "id:b", "feed:one", 20, "<entry>b</entry>"),
            ],
            storage.list_entries_by_recency(),
        )

        storage.delete_entry("entry:b")
        self.assertEqual(1, storage.entries_count())
        self.assertEqual(
            [("entry:a", "id:a2", "feed:two", 30, "<entry>a2</entry>")],
            storage.list_entries_by_recency(),
        )

        storage.delete_entry("missing")
        self.assertEqual(1, storage.entries_count())

    def test_clear_id_index_helper(self):
        storage.clear_id_index()

        index = storage.open_id_index(create=True)
        index["one"] = "feed:a"
        index["two"] = "feed:b"
        index.close()

        index = storage.open_id_index(create=False)
        self.assertEqual(2, len(index))
        index.close()

        storage.clear_id_index()

        index = storage.open_id_index(create=False)
        self.assertEqual(0, len(index))
        self.assertEqual([], index.keys())
        index.close()
