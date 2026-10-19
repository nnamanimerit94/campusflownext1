"""Validated, read-only current-state ticket statistics."""

from campusflow.models import (
    CATEGORIES, PRIORITIES, STATUSES, TicketStore, validate_store,
)


def ticket_statistics(store: TicketStore) -> dict:
    """Summarize the current validated store, including zero-count buckets.

    Reopened tickets count as open; historical transitions are not counted.
    """
    tickets = validate_store(store)
    by_status = {status: 0 for status in STATUSES}
    by_priority = {priority: 0 for priority in PRIORITIES}
    by_category = {category: 0 for category in CATEGORIES}
    unassigned = 0
    for ticket in tickets.values():
        by_status[ticket["status"]] += 1
        by_priority[ticket["priority"]] += 1
        by_category[ticket["category"]] += 1
        if ticket["assigned_to"] is None:
            unassigned += 1
    return {
        "total": len(tickets),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "unassigned": unassigned,
    }
