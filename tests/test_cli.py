"""Interactive CLI integration and persistence safety tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from campusflow.cli import main
from campusflow.storage import load_tickets, save_tickets
from campusflow.tickets import create_ticket


def scripted(answers, path):
    responses = iter(answers)
    output = []
    code = main(lambda _: next(responses), output.append, path)
    return code, output


class CliTests(TestCase):
    def test_create_persists_and_reload(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            answers = ["1", "S1", "Student", "Broken portal", "Cannot log in",
                       "technical", "high", "10", "10", "9", "12"]
            code, output = scripted(answers, path)
            self.assertEqual(code, 0)
            self.assertEqual(len(load_tickets(path)), 1)
            self.assertTrue(any("Saved:" in item for item in output))
            self.assertTrue(any("Reloaded 1 ticket" in item for item in output))
            self.assertTrue(any("'total': 1" in item for item in output))

    def test_invalid_count_does_not_write(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            code, output = scripted(["1", "S1", "Student", "Title", "Details",
                                     "other", "low", "bad", "12"], path)
            self.assertEqual(code, 0)
            self.assertFalse(path.exists())
            self.assertTrue(any("Operation failed" in line for line in output))

    def test_failed_save_does_not_publish_or_claim_success(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            answers = ["1", "S1", "Student", "Title", "Details", "other", "low",
                       "1", "9", "12"]
            with patch("campusflow.cli.save_tickets", side_effect=OSError("disk full")):
                # Unhandled programmer/unexpected OS errors should not be mistaken for success.
                with self.assertRaises(OSError):
                    scripted(answers, path)
            self.assertFalse(path.exists())

    def test_storage_failure_is_recoverable_and_no_false_success(self):
        from campusflow.models import StorageError
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            answers = ["1", "S1", "Student", "Title", "Details", "other", "low",
                       "1", "9", "12"]
            with patch("campusflow.cli.save_tickets", side_effect=StorageError("disk full")):
                code, output = scripted(answers, path)
            self.assertEqual(code, 0)
            self.assertFalse(any("Saved:" in line for line in output))
            self.assertTrue(any("active data unchanged" in line for line in output))
            self.assertTrue(any("'total': 0" in line for line in output))

    def test_corrupt_file_is_not_reset(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            path.write_text("not JSON")
            code, output = scripted([], path)
            self.assertEqual(code, 1)
            self.assertEqual(path.read_text(), "not JSON")
            self.assertTrue(any("Cannot load tickets" in line for line in output))

    def test_search_and_understanding_and_unknown_option(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            code, output = scripted(["99", "8", "", "", "", "", "",
                                     "11", "quit", "12"], path)
            self.assertEqual(code, 0)
            self.assertTrue(any("Unknown menu option" in line for line in output))
            self.assertIn("0 ticket(s)", output)
            self.assertTrue(any("Engineering Understanding Check" in line for line in output))

    def test_eof_exit(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            def eof(_):
                raise EOFError()
            output = []
            self.assertEqual(main(eof, output.append, path), 0)
            self.assertFalse(path.exists())

    def test_existing_ticket_lifecycle_notes_and_report(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.json"
            store = {}
            ticket = create_ticket(store, student_id="S1", student_name="Student",
                                   title="Network", description="Offline",
                                   category="technical", urgency="low", affected_users=1)
            save_tickets(path, store)
            ticket_id = ticket["id"]
            code, output = scripted(["2", ticket_id, "Operator",
                                     "3", ticket_id, "Operator", "Investigating",
                                     "4", ticket_id, "5", ticket_id, "6", ticket_id,
                                     "7", ticket_id, "12"], path)
            self.assertEqual(code, 0)
            loaded = load_tickets(path)[ticket_id]
            self.assertEqual(loaded["status"], "open")
            self.assertEqual(loaded["assigned_to"], "Operator")
            self.assertEqual(len(loaded["notes"]), 1)
            self.assertEqual(sum("Saved:" in line for line in output), 6)
