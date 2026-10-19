"""Read-only case-insensitive ticket search and combined filtering."""

from campusflow.models import (
    CATEGORIES, PRIORITIES, STATUSES, Ticket, TicketStore, ValidationError,
    parse_timestamp, validate_enum, validate_store,
)


def search_tickets(
    store: TicketStore, *, query: str = "", status: str | None = None,
    priority: str | None = None, category: str | None = None,
    assigned_to: str | None = None,
) -> list[Ticket]:
    """Return independently copied matches ordered by creation time then ID."""
    # Validate all inputs, including the store, even if there are no matches.
    tickets = validate_store(store)
    if not isinstance(query, str):
        raise ValidationError("query must be text")
    needle = query.strip().casefold()
    if status is not None:
        status = validate_enum(status, "status", STATUSES)
    if priority is not None:
        priority = validate_enum(priority, "priority", PRIORITIES)
    if category is not None:
        category = validate_enum(category, "category", CATEGORIES)
    if assigned_to is not None:
        if not isinstance(assigned_to, str) or not assigned_to.strip():
            raise ValidationError("assigned_to filter must be nonempty text")
        assigned_to = assigned_to.strip().casefold()

    matches: list[Ticket] = []
    for ticket in tickets.values():
        if status is not None and ticket["status"] != status:
            continue
        if priority is not None and ticket["priority"] != priority:
            continue
        if category is not None and ticket["category"] != category:
            continue
        if assigned_to is not None and (
            ticket["assigned_to"] is None
            or ticket["assigned_to"].casefold() != assigned_to
        ):
            continue
        fields = (
            ticket["id"], ticket["student_id"], ticket["student_name"],
            ticket["title"], ticket["description"],
            *(note["body"] for note in ticket["notes"]),
        )
        if needle and not any(needle in value.casefold() for value in fields):
            continue
        matches.append(ticket)
    return sorted(matches, key=lambda ticket: (parse_timestamp(ticket["created_at"]), ticket["id"]))
