"""Current-state reports, zero buckets, reopen and validation."""

from copy import deepcopy
from unittest import TestCase

from campusflow.models import CATEGORIES, PRIORITIES, STATUSES, ValidationError
from campusflow.reports import ticket_statistics
from campusflow.tickets import create_ticket
from campusflow.workflow import assign_ticket, reopen_ticket, transition_ticket


class ReportTests(TestCase):
    def setUp(self):
        self.store = {}

    def make(self, category="other", urgency="low", count=1):
        return create_ticket(
            self.store, student_id="S-1", student_name="Ada",
            title="Support", description="Help needed", category=category,
            urgency=urgency, affected_users=count,
        )["id"]

    def test_empty_store_has_all_zero_buckets(self):
        result = ticket_statistics({})
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["unassigned"], 0)
        self.assertEqual(result["by_status"], dict.fromkeys(STATUSES, 0))
        self.assertEqual(result["by_priority"], dict.fromkeys(PRIORITIES, 0))
        self.assertEqual(result["by_category"], dict.fromkeys(CATEGORIES, 0))

    def test_single_unassigned_ticket(self):
        self.make(category="technical", urgency="medium")
        result = ticket_statistics(self.store)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["unassigned"], 1)
        self.assertEqual(result["by_status"]["open"], 1)
        self.assertEqual(result["by_priority"]["medium"], 1)
        self.assertEqual(result["by_category"]["technical"], 1)

    def test_mixed_statuses_and_categories(self):
        ids = [
            self.make("payment", "high", 10),
            self.make("attendance", "low", 1),
            self.make("technical", "medium", 1),
            self.make("welfare", "low", 10),
        ]
        for tid in ids[:3]:
            assign_ticket(self.store, tid, "Mentor")
        transition_ticket(self.store, ids[0], "in_progress")
        transition_ticket(self.store, ids[0], "resolved")
        transition_ticket(self.store, ids[0], "closed")
        transition_ticket(self.store, ids[1], "in_progress")
        transition_ticket(self.store, ids[1], "resolved")
        transition_ticket(self.store, ids[2], "in_progress")
        result = ticket_statistics(self.store)
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["by_status"], {
            "open": 1, "in_progress": 1, "resolved": 1, "closed": 1,
        })
        self.assertEqual(result["by_priority"], {
            "low": 1, "medium": 2, "high": 0, "critical": 1,
        })
        self.assertEqual(result["by_category"], {
            "payment": 1, "attendance": 1, "technical": 1,
            "welfare": 1, "other": 0,
        })
        self.assertEqual(result["unassigned"], 1)

    def test_reopened_ticket_is_counted_in_current_status(self):
        tid = self.make()
        assign_ticket(self.store, tid, "Mentor")
        transition_ticket(self.store, tid, "in_progress")
        transition_ticket(self.store, tid, "resolved")
        before = ticket_statistics(self.store)
        self.assertEqual(before["by_status"]["resolved"], 1)
        reopen_ticket(self.store, tid)
        after = ticket_statistics(self.store)
        self.assertEqual(after["by_status"]["resolved"], 0)
        self.assertEqual(after["by_status"]["open"], 1)
        self.assertEqual(after["unassigned"], 0)

    def test_report_does_not_mutate_store(self):
        self.make()
        before = deepcopy(self.store)
        ticket_statistics(self.store)
        self.assertEqual(self.store, before)

    def test_report_result_does_not_alias_future_results(self):
        self.make()
        first = ticket_statistics(self.store)
        first["by_status"]["open"] = 999
        first["by_category"].clear()
        second = ticket_statistics(self.store)
        self.assertEqual(second["by_status"]["open"], 1)
        self.assertEqual(second["by_category"]["other"], 1)

    def test_corrupt_ticket_rejected_without_mutation(self):
        tid = self.make()
        self.store[tid]["priority"] = "critical"
        before = deepcopy(self.store)
        with self.assertRaises(ValidationError):
            ticket_statistics(self.store)
        self.assertEqual(self.store, before)

    def test_invalid_store_types_rejected(self):
        for value in (None, [], "text", 2, True):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    ticket_statistics(value)

    def test_priority_impact_critical_and_zero_high(self):
        self.make(urgency="high", count=10)
        self.make(urgency="medium", count=10)
        result = ticket_statistics(self.store)
        self.assertEqual(result["by_priority"]["critical"], 1)
        self.assertEqual(result["by_priority"]["high"], 1)
        self.assertEqual(result["by_priority"]["low"], 0)
