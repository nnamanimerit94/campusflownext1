"""Ticket contracts, adversarial inputs and rejected-operation integrity."""

from copy import deepcopy
from uuid import UUID, uuid4, uuid1
import unittest
from unittest.mock import patch

from campusflow.models import (
    CATEGORIES, TEXT_LIMITS, ValidationError, TicketNotFoundError,
    validate_ticket, validate_store,
)
from campusflow.tickets import create_ticket, calculate_priority, get_ticket


INPUT = dict(student_id="ST-1", student_name="Ada", title="Payment issue",
             description="Payment has not arrived", category="payment",
             urgency="high", affected_users=1)


def make_ticket():
    return create_ticket({}, **INPUT)


class PriorityTests(unittest.TestCase):
    def test_all_cells_and_boundaries(self):
        for urgency, normal, escalated in (("low", "low", "medium"),
                                          ("medium", "medium", "high"),
                                          ("high", "high", "critical")):
            for count in (1, 9, 10, 11, 1000000):
                with self.subTest(urgency=urgency, count=count):
                    self.assertEqual(calculate_priority(urgency, count),
                                     normal if count < 10 else escalated)

    def test_invalid_priority_inputs(self):
        for urgency in (None, [], 1, True, "HIGH", " high ", "critical", ""):
            with self.subTest(urgency=urgency), self.assertRaises(ValidationError):
                calculate_priority(urgency, 1)
        for count in (None, [], {}, True, False, 1.0, "10", 0, -1):
            with self.subTest(count=count), self.assertRaises(ValidationError):
                calculate_priority("high", count)


class CreationTests(unittest.TestCase):
    def test_initial_state_normalization_and_isolation(self):
        store = {}
        ticket = create_ticket(store, **{**INPUT, "student_name": "  Ada  "})
        self.assertEqual(ticket["student_name"], "Ada")
        self.assertEqual(UUID(ticket["id"]).version, 4)
        self.assertEqual(str(UUID(ticket["id"])), ticket["id"])
        self.assertEqual(ticket["status"], "open")
        self.assertIsNone(ticket["assigned_to"])
        self.assertEqual(ticket["created_at"], ticket["updated_at"])
        self.assertEqual(ticket["notes"], [])
        ticket["notes"].append({})
        ticket["title"] = "changed"
        self.assertEqual(store[ticket["id"]]["notes"], [])
        self.assertEqual(store[ticket["id"]]["title"], INPUT["title"])

    def test_invalid_inputs_preserve_existing_store(self):
        existing = make_ticket()
        store = {existing["id"]: existing}
        for field, bad_values in {
            **{key: (None, [], 42, True, "", " \n ", "x" * (limit + 1))
               for key, limit in TEXT_LIMITS.items()},
            "category": (None, [], "unknown", "Payment", " payment "),
            "urgency": (None, [], "urgent"),
            "affected_users": (None, True, 0, -1, "2", 2.0),
        }.items():
            for value in bad_values:
                before = deepcopy(store)
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    create_ticket(store, **{**INPUT, field: value})
                self.assertEqual(store, before)

    def test_exact_text_limits_and_categories(self):
        for field, limit in TEXT_LIMITS.items():
            self.assertEqual(len(create_ticket({}, **{**INPUT, field: "x" * limit})[field]), limit)
        for category in CATEGORIES:
            self.assertEqual(create_ticket({}, **{**INPUT, "category": category})["category"], category)

    def test_collision_retries_then_succeeds(self):
        old = make_ticket()
        store = {old["id"]: old}
        fresh = uuid4()
        with patch("campusflow.tickets.uuid4", side_effect=[UUID(old["id"]), fresh]) as generator:
            new = create_ticket(store, **INPUT)
        self.assertEqual(generator.call_count, 2)
        self.assertEqual(new["id"], str(fresh))
        self.assertEqual(store[old["id"]], old)

    def test_collision_exhaustion_is_atomic(self):
        old = make_ticket()
        store = {old["id"]: old}
        before = deepcopy(store)
        with patch("campusflow.tickets.uuid4", return_value=UUID(old["id"])) as generator:
            with self.assertRaises(ValidationError):
                create_ticket(store, **INPUT)
        self.assertEqual(generator.call_count, 11)
        self.assertEqual(store, before)

    def test_invalid_store_and_generator_leave_input_unchanged(self):
        for store in (None, [], {"bad": {}}):
            before = deepcopy(store)
            with self.assertRaises(ValidationError):
                create_ticket(store, **INPUT)
            self.assertEqual(store, before)
        store = {}
        with patch("campusflow.tickets.uuid4", return_value=uuid1()):
            with self.assertRaises(ValidationError):
                create_ticket(store, **INPUT)
        self.assertEqual(store, {})


class LookupTests(unittest.TestCase):
    def test_missing_valid_id(self):
        with self.assertRaises(TicketNotFoundError):
            get_ticket({}, str(uuid4()))

    def test_malformed_ids_are_validation_errors(self):
        good = str(uuid4())
        for value in (None, True, 3, [], {}, "", good.upper(), good.replace("-", ""),
                      " " + good, "{" + good + "}", str(uuid1()), "not-a-uuid"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                get_ticket({}, value)

    def test_lookup_returns_deep_copy_and_does_not_mutate(self):
        ticket = make_ticket()
        store = {ticket["id"]: ticket}
        before = deepcopy(store)
        found = get_ticket(store, ticket["id"])
        found["notes"].append({})
        self.assertEqual(store, before)
        with self.assertRaises(TicketNotFoundError):
            get_ticket(store, str(uuid4()))
        self.assertEqual(store, before)


class SchemaTests(unittest.TestCase):
    def assert_rejected(self, ticket):
        before = deepcopy(ticket)
        with self.assertRaises(ValidationError):
            validate_ticket(ticket)
        self.assertEqual(ticket, before)

    def test_exact_schema_and_types(self):
        ticket = make_ticket()
        for field in ticket:
            missing = deepcopy(ticket)
            del missing[field]
            self.assert_rejected(missing)
        self.assert_rejected({**ticket, "extra": 1})
        for value in (None, [], "ticket"):
            self.assert_rejected(value)
        for field, value in (("priority", "critical"), ("status", "pending"),
                             ("notes", {}), ("student_name", " Ada "),
                             ("assigned_to", ""), ("affected_users", True)):
            self.assert_rejected({**ticket, field: value})

    def test_assignment_invariants(self):
        for status in ("in_progress", "resolved", "closed"):
            ticket = {**make_ticket(), "status": status}
            self.assert_rejected(ticket)
            ticket["assigned_to"] = "Mentor"
            self.assertEqual(validate_ticket(ticket), ticket)

    def test_timestamps(self):
        ticket = make_ticket()
        for value in (None, [], "bad", "2026-01-01", "2026-01-01T00:00:00",
                      "2026-01-01T00:00:00+01:00"):
            for field in ("created_at", "updated_at"):
                self.assert_rejected({**ticket, field: value})
        self.assert_rejected({**ticket, "updated_at": "2000-01-01T00:00:00Z"})

    def test_nested_note_schema_without_note_operations(self):
        ticket = make_ticket()
        note = dict(id=str(uuid4()), author="Mentor", body="Checking",
                    created_at=ticket["created_at"])
        ticket["notes"] = [note]
        validated = validate_ticket(ticket)
        validated["notes"][0]["body"] = "changed"
        self.assertEqual(note["body"], "Checking")
        self.assert_rejected({**ticket, "notes": [note, deepcopy(note)]})
        for bad in (None, {}, {**note, "id": str(uuid1())}, {**note, "author": " "},
                    {**note, "body": "x" * 5001}, {**note, "extra": 1},
                    {**note, "created_at": "2000-01-01T00:00:00Z"},
                    {**note, "created_at": "2100-01-01T00:00:00Z"}):
            self.assert_rejected({**ticket, "notes": [bad]})

    def test_store_validation_and_copy(self):
        ticket = make_ticket()
        store = {ticket["id"]: ticket}
        result = validate_store(store)
        result[ticket["id"]]["notes"].append({})
        self.assertEqual(ticket["notes"], [])
        for value in (None, [], {str(uuid4()): ticket}, {"bad": ticket},
                      {ticket["id"]: {**ticket, "priority": "critical"}}):
            before = deepcopy(value)
            with self.assertRaises(ValidationError):
                validate_store(value)
            self.assertEqual(value, before)


if __name__ == "__main__":
    unittest.main()
