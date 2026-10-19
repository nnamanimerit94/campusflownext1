"""Search contracts: text, filters, ordering, validation and isolation."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from campusflow.models import ValidationError
from campusflow.notes import add_note
from campusflow.tickets import create_ticket
from campusflow.workflow import assign_ticket, transition_ticket
from campusflow.search import search_tickets


class SearchTests(TestCase):
    def setUp(self):
        self.store = {}
        self.a = self.make("S-1", "Adé", "Network Failure", "WiFi offline",
                           "technical", "high", 10)
        self.b = self.make("S-2", "Ben", "Attendance Query", "Missed class",
                           "attendance", "low", 1)
        self.c = self.make("S-3", "Ada", "Payment", "Invoice overdue",
                           "payment", "medium", 1)
        add_note(self.store, self.a, author="Mentor", body="Router Reboot ✓")
        assign_ticket(self.store, self.a, " Mentor ")
        transition_ticket(self.store, self.a, "in_progress")
        assign_ticket(self.store, self.c, "mentor")

    def make(self, sid, name, title, description, category, urgency, affected):
        return create_ticket(self.store, student_id=sid, student_name=name,
                             title=title, description=description, category=category,
                             urgency=urgency, affected_users=affected)["id"]

    def ids(self, **kwargs):
        return {t["id"] for t in search_tickets(self.store, **kwargs)}

    def test_empty_query_and_whitespace_return_everything(self):
        for query in ("", "  ", "\n\t"):
            with self.subTest(query=query):
                self.assertEqual(self.ids(query=query), {self.a, self.b, self.c})

    def test_search_all_text_fields(self):
        for text, expected in (
            (self.a, self.a), ("S-1", self.a), ("ADÉ", self.a),
            ("network", self.a), ("wifi", self.a), ("REBOOT", self.a),
            ("S-2", self.b), ("ben", self.b), ("attendance", self.b),
            ("missed", self.b), ("INVOICE", self.c),
        ):
            with self.subTest(text=text):
                self.assertEqual(self.ids(query=f"  {text}  "), {expected})

    def test_query_casefold_and_unicode(self):
        self.assertEqual(self.ids(query="router reboot ✓"), {self.a})
        self.assertEqual(self.ids(query="not found"), set())

    def test_enum_filters(self):
        self.assertEqual(self.ids(status="in_progress"), {self.a})
        self.assertEqual(self.ids(status="open"), {self.b, self.c})
        self.assertEqual(self.ids(priority="critical"), {self.a})
        self.assertEqual(self.ids(priority="low"), {self.b})
        self.assertEqual(self.ids(category="payment"), {self.c})

    def test_assignee_exact_casefold(self):
        self.assertEqual(self.ids(assigned_to=" MENTOR "), {self.a, self.c})
        self.assertEqual(self.ids(assigned_to="men"), set())
        self.assertEqual(self.ids(assigned_to="unknown"), set())

    def test_filters_are_and(self):
        self.assertEqual(self.ids(query="router", status="in_progress",
                                  priority="critical", category="technical",
                                  assigned_to="mentor"), {self.a})
        self.assertEqual(self.ids(query="router", status="open"), set())
        self.assertEqual(self.ids(category="payment", assigned_to="mentor"), {self.c})

    def test_invalid_query_and_filters_preserve_store(self):
        for field, values in (
            ("query", (None, 1, [], True)),
            ("status", ("OPEN", "invalid", [], True)),
            ("priority", ("urgent", "CRITICAL", [], True)),
            ("category", ("TECHNICAL", "invalid", [], True)),
            ("assigned_to", ("", " \t ", [], True, 1)),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    before = deepcopy(self.store)
                    with self.assertRaises(ValidationError):
                        search_tickets(self.store, **{field: value})
                    self.assertEqual(self.store, before)

    def test_no_filters_do_not_mutate(self):
        before = deepcopy(self.store)
        search_tickets(self.store, query="x")
        self.assertEqual(self.store, before)

    def test_result_isolation(self):
        before = deepcopy(self.store)
        matches = search_tickets(self.store, query="reboot")
        matches[0]["notes"][0]["body"] = "tampered"
        matches[0]["student_name"] = "Changed"
        self.assertEqual(self.store, before)

    def test_created_time_order_then_id_tie(self):
        now = datetime.now(timezone.utc)
        for tid in (self.a, self.b, self.c):
            self.store[tid]["created_at"] = (now - timedelta(days=1)).isoformat()
            self.store[tid]["updated_at"] = now.isoformat()
        self.store[self.a]["created_at"] = (now - timedelta(days=2)).isoformat()
        self.store[self.a]["notes"][0]["created_at"] = now.isoformat()
        results = search_tickets(self.store)
        self.assertEqual([r["id"] for r in results],
                         [self.a] + sorted((self.b, self.c)))

    def test_invalid_store_rejected(self):
        before = deepcopy(self.store)
        self.store[self.a]["priority"] = "low"
        with self.assertRaises(ValidationError):
            search_tickets(self.store)
        self.assertEqual(self.store[self.b], before[self.b])

    def test_allows_empty_store(self):
        self.assertEqual(search_tickets({}, query="anything"), [])
