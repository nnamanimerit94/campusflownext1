"""Validated ticket assignment and lifecycle operations."""

from datetime import datetime, timezone

from campusflow.models import (
    InvalidTransitionError, Ticket, TicketStore, ValidationError,
    clean_text, parse_timestamp, validate_enum, validate_ticket, STATUSES,
)
from campusflow.tickets import get_ticket


_ALLOWED = {"open": "in_progress", "in_progress": "resolved", "resolved": "closed"}


def _publish(store: TicketStore, ticket_id: str, ticket: Ticket) -> Ticket:
    previous = parse_timestamp(ticket["updated_at"])
    ticket["updated_at"] = max(datetime.now(timezone.utc), previous).isoformat()
    validated = validate_ticket(ticket)
    store[ticket_id] = validated
    return validate_ticket(validated)


def assign_ticket(store: TicketStore, ticket_id: str, assignee: str) -> Ticket:
    """Assign or reassign an active ticket, without partial mutation."""
    ticket = get_ticket(store, ticket_id)
    normalized = clean_text(assignee, "assignee", 120)
    if ticket["status"] not in ("open", "in_progress"):
        raise InvalidTransitionError("Only open or in-progress tickets can be assigned")
    if ticket["assigned_to"] == normalized:
        raise InvalidTransitionError("Ticket is already assigned to this person")
    ticket["assigned_to"] = normalized
    return _publish(store, ticket_id, ticket)


def transition_ticket(store: TicketStore, ticket_id: str, new_status: str) -> Ticket:
    """Move one step through the approved forward-only lifecycle."""
    ticket = get_ticket(store, ticket_id)
    status = validate_enum(new_status, "status", STATUSES)
    if _ALLOWED.get(ticket["status"]) != status:
        raise InvalidTransitionError("Disallowed ticket status transition")
    if status == "in_progress" and ticket["assigned_to"] is None:
        raise InvalidTransitionError("Assign the ticket before starting work")
    return _publish(store, ticket_id, {**ticket, "status": status})


def reopen_ticket(store: TicketStore, ticket_id: str) -> Ticket:
    """Reopen a resolved or closed ticket while retaining its history."""
    ticket = get_ticket(store, ticket_id)
    if ticket["status"] not in ("resolved", "closed"):
        raise InvalidTransitionError("Only resolved or closed tickets can be reopened")
    return _publish(store, ticket_id, {**ticket, "status": "open"})
