"""Lifecycle matrix, validation, and rejected-operation integrity."""

from copy import deepcopy
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from campusflow.models import InvalidTransitionError, TicketNotFoundError, ValidationError, validate_store
from campusflow.notes import add_note
from campusflow.tickets import create_ticket
from campusflow.workflow import assign_ticket, transition_ticket, reopen_ticket


class LifecycleTests(TestCase):
    def setUp(self):
        self.store = {}
        ticket = create_ticket(
            self.store, student_id="S1", student_name="Ada", title="Help",
            description="Need support", category="technical", urgency="high",
            affected_users=10,
        )
        self.id = ticket["id"]

    def _status(self, status):
        ticket = self.store[self.id]
        ticket["status"] = status
        ticket["assigned_to"] = None if status == "open" else "Mentor"

    def _rejected(self, operation, error):
        before = deepcopy(self.store)
        with self.assertRaises(error):
            operation()
        self.assertEqual(self.store, before)

    def test_forward_lifecycle(self):
        self._rejected(lambda: transition_ticket(self.store, self.id, "in_progress"), InvalidTransitionError)
        assigned = assign_ticket(self.store, self.id, " Mentor ")
        self.assertEqual(assigned["assigned_to"], "Mentor")
        for status in ("in_progress", "resolved", "closed"):
            result = transition_ticket(self.store, self.id, status)
            self.assertEqual(result["status"], status)
            validate_store(self.store)

    def test_complete_transition_matrix(self):
        allowed = {"open": "in_progress", "in_progress": "resolved", "resolved": "closed"}
        for source in ("open", "in_progress", "resolved", "closed"):
            for target in ("open", "in_progress", "resolved", "closed"):
                with self.subTest(source=source, target=target):
                    self._status(source)
                    if target == allowed.get(source):
                        if source == "open":
                            self.store[self.id]["assigned_to"] = "Mentor"
                        self.assertEqual(transition_ticket(self.store, self.id, target)["status"], target)
                    else:
                        self._rejected(lambda: transition_ticket(self.store, self.id, target), InvalidTransitionError)

    def test_invalid_status_and_missing_ids(self):
        for value in ("", "OPEN", "pending", None, True, [], 2):
            with self.subTest(value=value):
                self._rejected(lambda: transition_ticket(self.store, self.id, value), ValidationError)
        self._rejected(lambda: reopen_ticket(self.store, "invalid"), ValidationError)
        self._rejected(lambda: assign_ticket(self.store, str(uuid4()), "Mentor"), TicketNotFoundError)

    def test_assignment_rules(self):
        for status in ("open", "in_progress"):
            self._status(status)
            self.assertEqual(assign_ticket(self.store, self.id, "New Mentor")["assigned_to"], "New Mentor")
            self._rejected(lambda: assign_ticket(self.store, self.id, " New Mentor "), InvalidTransitionError)
        for status in ("resolved", "closed"):
            self._status(status)
            self._rejected(lambda: assign_ticket(self.store, self.id, "Another"), InvalidTransitionError)

    def test_invalid_assignee(self):
        for value in ("", "  ", None, True, [], 3, "x" * 121):
            with self.subTest(value=value):
                self._rejected(lambda: assign_ticket(self.store, self.id, value), ValidationError)

    def test_reopen_matrix_and_history(self):
        assign_ticket(self.store, self.id, "Mentor")
        first = add_note(self.store, self.id, author="Mentor", body="Working")
        original = deepcopy(self.store[self.id])
        for status in ("resolved", "closed"):
            self._status(status)
            reopened = reopen_ticket(self.store, self.id)
            self.assertEqual(reopened["status"], "open")
            for field in ("id", "created_at", "priority", "assigned_to", "notes"):
                self.assertEqual(reopened[field], original[field])
            self._rejected(lambda: reopen_ticket(self.store, self.id), InvalidTransitionError)
            self.assertEqual(add_note(self.store, self.id, author="Mentor", body="Followup")["author"], "Mentor")
        self.assertEqual(first["body"], "Working")

    def test_reopen_rejects_active_states(self):
        for status in ("open", "in_progress"):
            self._status(status)
            self._rejected(lambda: reopen_ticket(self.store, self.id), InvalidTransitionError)

    def test_other_tickets_and_return_copies(self):
        other = create_ticket(self.store, student_id="S2", student_name="Ben",
            title="Other", description="Other issue", category="other",
            urgency="low", affected_users=1)
        before = deepcopy(self.store[other["id"]])
        old = self.store[self.id]
        result = assign_ticket(self.store, self.id, "Mentor")
        result["notes"].append({})
        result["assigned_to"] = "Changed"
        self.assertEqual(self.store[other["id"]], before)
        self.assertIsNone(old["assigned_to"])
        self.assertEqual(self.store[self.id]["assigned_to"], "Mentor")

    def test_monotonic_timestamps(self):
        assign_ticket(self.store, self.id, "Mentor")
        prior = self.store[self.id]["updated_at"]
        with patch("campusflow.workflow.datetime") as clock:
            clock.now.return_value = datetime(2000, 1, 1, tzinfo=timezone.utc)
            result = transition_ticket(self.store, self.id, "in_progress")
        self.assertEqual(result["updated_at"], prior)
        validate_store(self.store)

    def test_invalid_store_is_unchanged(self):
        self.store[self.id]["priority"] = "wrong"
        self._rejected(lambda: assign_ticket(self.store, self.id, "Mentor"), ValidationError)
