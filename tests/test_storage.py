#!/usr/bin/env python

import os
import shutil
import sqlite3
import unittest

from planet import config, storage


WORKDIR = "tests/work/storage/cache"
CONFIGFILE = "tests/data/storage/config.ini"


class StorageTest(unittest.TestCase):
    def tearDown(self):
        if os.path.exists(WORKDIR):
            shutil.rmtree(WORKDIR)
            os.removedirs(os.path.split(WORKDIR)[0])

    def test_open_id_index_returns_none_without_database(self):
        config.load(CONFIGFILE)
        self.assertIsNone(storage.open_id_index(create=False))

    def test_schema_and_id_index_crud(self):
        config.load(CONFIGFILE)
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
