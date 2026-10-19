"""Structured note contracts and failure-path data integrity."""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid1, uuid4
import unittest
from unittest.mock import patch

from campusflow.models import (
    InvalidTransitionError, TicketNotFoundError, ValidationError, parse_timestamp,
    validate_store,
)
from campusflow.notes import add_note
from campusflow.tickets import create_ticket


class NoteTests(unittest.TestCase):
    def setUp(self):
        self.store = {}
        ticket = create_ticket(self.store, student_id="ST-1", student_name="Ada",
                               title="Help", description="Need support", category="other",
                               urgency="low", affected_users=1)
        self.ticket_id = ticket["id"]

    def add(self, **changes):
        return add_note(self.store, self.ticket_id, **{ "author": "Mentor", "body": "Following up", **changes})

    def test_active_states_and_normalized_text(self):
        for status in ("open", "in_progress"):
            with self.subTest(status=status):
                self.store[self.ticket_id]["status"] = status
                self.store[self.ticket_id]["assigned_to"] = "Mentor"
                note = self.add(author="  Mentor  ", body="  Following\nup  ")
                self.assertEqual(note["author"], "Mentor")
                self.assertEqual(note["body"], "Following\nup")
                self.assertEqual(str(UUID(note["id"])), note["id"])
                self.assertEqual(UUID(note["id"]).version, 4)
                self.assertEqual(note["created_at"], self.store[self.ticket_id]["updated_at"])
                self.assertGreaterEqual(parse_timestamp(note["created_at"]),
                                        parse_timestamp(self.store[self.ticket_id]["created_at"]))
                validate_store(self.store)

    def test_exact_limits(self):
        note = self.add(author="a" * 120, body="b" * 5000)
        self.assertEqual(len(note["author"]), 120)
        self.assertEqual(len(note["body"]), 5000)

    def test_invalid_text_is_atomic(self):
        self.add()
        for field, limit in (("author", 120), ("body", 5000)):
            for value in (None, True, 1, [], {}, "", " \n\t", "x" * (limit + 1)):
                before = deepcopy(self.store)
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    self.add(**{field: value})
                self.assertEqual(self.store, before)

    def test_completed_states_reject_and_preserve_notes(self):
        self.add()
        for status in ("resolved", "closed"):
            self.store[self.ticket_id]["status"] = status
            self.store[self.ticket_id]["assigned_to"] = "Mentor"
            before = deepcopy(self.store)
            with self.subTest(status=status), self.assertRaises(InvalidTransitionError):
                self.add()
            self.assertEqual(self.store, before)

    def test_missing_and_malformed_ticket_ids(self):
        for value, error in ((str(uuid4()), TicketNotFoundError), (None, ValidationError),
                             ([], ValidationError), ("bad", ValidationError),
                             (self.ticket_id.upper(), ValidationError)):
            before = deepcopy(self.store)
            with self.subTest(value=value), self.assertRaises(error):
                add_note(self.store, value, author="Mentor", body="Update")
            self.assertEqual(self.store, before)

    def test_preserves_existing_notes_and_other_tickets(self):
        first = self.add()
        other = create_ticket(self.store, student_id="ST-2", student_name="Ben",
                              title="Help", description="Other", category="other",
                              urgency="low", affected_users=1)
        before = deepcopy(self.store)
        second = self.add(body="Second")
        current = self.store[self.ticket_id]
        self.assertEqual(current["notes"], [first, second])
        self.assertEqual(self.store[other["id"]], before[other["id"]])
        for field in current:
            if field not in ("notes", "updated_at"):
                self.assertEqual(current[field], before[self.ticket_id][field])

    def test_return_and_previous_snapshots_are_isolated(self):
        original = self.store[self.ticket_id]
        note = self.add()
        note["body"] = "Changed outside store"
        self.assertEqual(self.store[self.ticket_id]["notes"][0]["body"], "Following up")
        self.assertEqual(original["notes"], [])

    def test_collision_retry_preserves_prior_note(self):
        first = self.add()
        fresh = uuid4()
        with patch("campusflow.notes.uuid4", side_effect=[UUID(first["id"]), fresh]) as generator:
            second = self.add()
        self.assertEqual(generator.call_count, 2)
        self.assertEqual(second["id"], str(fresh))
        self.assertEqual(self.store[self.ticket_id]["notes"][0], first)

    def test_collision_exhaustion_is_atomic(self):
        first = self.add()
        before = deepcopy(self.store)
        with patch("campusflow.notes.uuid4", return_value=UUID(first["id"])) as generator:
            with self.assertRaises(ValidationError):
                self.add()
        self.assertEqual(generator.call_count, 11)
        self.assertEqual(self.store, before)

    def test_invalid_generated_uuid_is_atomic(self):
        before = deepcopy(self.store)
        with patch("campusflow.notes.uuid4", return_value=uuid1()):
            with self.assertRaises(ValidationError):
                self.add()
        self.assertEqual(self.store, before)

    def test_backward_clock_does_not_regress_timestamps(self):
        self.add()
        previous = self.store[self.ticket_id]["updated_at"]
        with patch("campusflow.notes.datetime") as clock:
            clock.now.return_value = datetime(2000, 1, 1, tzinfo=timezone.utc)
            note = self.add()
        self.assertEqual(parse_timestamp(note["created_at"]), parse_timestamp(previous))
        self.assertEqual(note["created_at"], self.store[self.ticket_id]["updated_at"])
        validate_store(self.store)

    def test_corrupt_store_is_rejected_without_mutation(self):
        self.add()
        self.store[self.ticket_id]["notes"].append(deepcopy(self.store[self.ticket_id]["notes"][0]))
        before = deepcopy(self.store)
        with self.assertRaises(ValidationError):
            self.add()
        self.assertEqual(self.store, before)


if __name__ == "__main__":
    unittest.main()
