"""Real-filesystem round trips and injected failure-path integrity checks."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from campusflow.models import StorageError
from campusflow.notes import add_note
from campusflow.storage import load_tickets, save_tickets
from campusflow.tickets import create_ticket


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "tickets.json"
        self.store = {}
        ticket = create_ticket(self.store, student_id="ST-1", student_name="Adé",
                               title="Help", description="Payment ₦", category="payment",
                               urgency="high", affected_users=10)
        add_note(self.store, ticket["id"], author="Mentor", body="Checking ✓")

    def assert_bad_file(self, text):
        self.path.write_text(text, encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(StorageError) as caught:
            load_tickets(self.path)
        self.assertIsNotNone(caught.exception.__cause__)
        self.assertEqual(self.path.read_bytes(), before)

    def test_save_reload_notes_unicode_and_independent_results(self):
        before = deepcopy(self.store)
        save_tickets(self.path, self.store)
        self.assertEqual(self.store, before)
        loaded = load_tickets(self.path)
        self.assertEqual(loaded, self.store)
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(envelope["schema_version"], 1)
        self.assertIsInstance(envelope["tickets"], list)
        next(iter(loaded.values()))["notes"][0]["body"] = "Changed"
        self.assertEqual(load_tickets(self.path), self.store)
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_empty_store_roundtrip(self):
        save_tickets(self.path, {})
        self.assertEqual(load_tickets(self.path), {})

    def test_missing_file_does_not_create_files(self):
        self.assertEqual(load_tickets(self.path), {})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_json_and_nonstandard_constants(self):
        for text in ("", " ", "{", '{"schema_version":1,"tickets":[] trailing}',
                     '{"schema_version":NaN,"tickets":[]}',
                     '{"schema_version":Infinity,"tickets":[]}'):
            with self.subTest(text=text):
                self.assert_bad_file(text)

    def test_invalid_encoding(self):
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaises(StorageError) as caught:
            load_tickets(self.path)
        self.assertIsInstance(caught.exception.__cause__, UnicodeError)
        self.assertEqual(self.path.read_bytes(), b"\xff\xfe")

    def test_schema_versions_and_envelopes(self):
        for value in (None, [], {}, {"schema_version": 1},
                      {"schema_version": 1, "tickets": [], "extra": 1},
                      *({"schema_version": v, "tickets": []} for v in (True, False, 0, 2, "1", 1.0)),
                      {"schema_version": 1, "tickets": {}},
                      {"schema_version": 1, "tickets": [None]}):
            with self.subTest(value=value):
                self.assert_bad_file(json.dumps(value))

    def test_duplicate_ticket_ids(self):
        record = next(iter(self.store.values()))
        self.assert_bad_file(json.dumps({"schema_version": 1, "tickets": [record, record]}))

    def test_duplicate_json_keys(self):
        self.assert_bad_file('{"schema_version":1,"schema_version":1,"tickets":[]}')

    def test_invalid_record_and_duplicate_notes(self):
        record = deepcopy(next(iter(self.store.values())))
        for invalid in ({**record, "priority": "low"}, {**record, "extra": 1},
                        {**record, "notes": record["notes"] * 2}):
            self.assert_bad_file(json.dumps({"schema_version": 1, "tickets": [invalid]}))

    def test_invalid_store_does_not_touch_existing_file(self):
        self.path.write_bytes(b"previous bytes")
        for value in (None, [], {"bad": {}}, {next(iter(self.store)): {}}):
            before = deepcopy(value)
            with self.assertRaises(StorageError) as caught:
                save_tickets(self.path, value)
            self.assertIsNotNone(caught.exception.__cause__)
            self.assertEqual(value, before)
            self.assertEqual(self.path.read_bytes(), b"previous bytes")
            self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_fsync_and_replace_failures_preserve_bytes_and_cleanup(self):
        save_tickets(self.path, self.store)
        before = self.path.read_bytes()
        for target in ("campusflow.storage.os.fsync", "campusflow.storage.os.replace",
                       "campusflow.storage.tempfile.NamedTemporaryFile"):
            with self.subTest(target=target), patch(target, side_effect=OSError("injected failure")):
                with self.assertRaises(StorageError) as caught:
                    save_tickets(self.path, {})
                self.assertIsInstance(caught.exception.__cause__, OSError)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(load_tickets(self.path), self.store)
            self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_write_and_flush_failures_cleanup(self):
        self.path.write_bytes(b"original")
        real_factory = tempfile.NamedTemporaryFile
        for stage in ("write", "flush"):
            class FailingFile:
                def __enter__(inner):
                    inner.real = real_factory(mode="w", encoding="utf-8", dir=self.root, delete=False)
                    inner.name = inner.real.name
                    return inner

                def __exit__(inner, *args):
                    inner.real.close()

                def write(inner, payload):
                    inner.real.write(payload[:10])
                    if stage == "write":
                        raise OSError("partial write")

                def flush(inner):
                    raise OSError("flush failed")

            with self.subTest(stage=stage), patch("campusflow.storage.tempfile.NamedTemporaryFile", return_value=FailingFile()):
                with self.assertRaises(StorageError):
                    save_tickets(self.path, self.store)
            self.assertEqual(self.path.read_bytes(), b"original")
            self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_missing_parent_and_directory_target_fail(self):
        with self.assertRaises(StorageError):
            save_tickets(self.root / "absent" / "tickets.json", self.store)
        with self.assertRaises(StorageError):
            save_tickets(self.root, self.store)
        with self.assertRaises(StorageError):
            load_tickets(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_read_permission_error_is_not_empty_store(self):
        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            with self.assertRaises(StorageError) as caught:
                load_tickets(self.path)
        self.assertIsInstance(caught.exception.__cause__, PermissionError)

    def test_replacement_is_same_directory_and_after_fsync(self):
        import os
        events = []
        real_sync, real_replace = os.fsync, os.replace

        def sync(fd):
            events.append("sync")
            return real_sync(fd)

        def replace(source, target):
            self.assertEqual(Path(source).parent, self.path.parent)
            self.assertEqual(target, self.path)
            self.assertEqual(events, ["sync"])
            events.append("replace")
            return real_replace(source, target)

        with patch("campusflow.storage.os.fsync", side_effect=sync), patch("campusflow.storage.os.replace", side_effect=replace):
            save_tickets(self.path, self.store)
        self.assertEqual(events, ["sync", "replace"])


if __name__ == "__main__":
    unittest.main()
