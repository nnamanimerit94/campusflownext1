"""Validated in-memory creation, deterministic priority and safe lookup."""

from datetime import datetime, timezone
from uuid import uuid4

from campusflow.models import (
    CATEGORIES, TEXT_LIMITS, Ticket, TicketNotFoundError, TicketStore,
    ValidationError, clean_text, priority_for, validate_enum, validate_store,
    validate_ticket, validate_uuid,
)


def calculate_priority(urgency: str, affected_users: int) -> str:
    return priority_for(urgency, affected_users)


def create_ticket(
    store: TicketStore, *, student_id: str, student_name: str, title: str,
    description: str, category: str, urgency: str, affected_users: int,
) -> Ticket:
    """Validate before insertion; no failure path partially updates the store."""
    validate_store(store)
    values = {"student_id": student_id, "student_name": student_name,
              "title": title, "description": description}
    text = {key: clean_text(value, key, TEXT_LIMITS[key]) for key, value in values.items()}
    category = validate_enum(category, "category", CATEGORIES)
    priority = calculate_priority(urgency, affected_users)
    # Initial candidate plus at most ten retries, as specified in the plan.
    for _ in range(11):
        ticket_id = validate_uuid(str(uuid4()))
        if ticket_id not in store:
            break
    else:
        raise ValidationError("Could not allocate a unique ticket ID after ten retries")
    now = datetime.now(timezone.utc).isoformat()
    ticket = validate_ticket({
        **text, "id": ticket_id, "category": category, "urgency": urgency,
        "affected_users": affected_users, "priority": priority, "status": "open",
        "assigned_to": None, "created_at": now, "updated_at": now, "notes": [],
    })
    returned = validate_ticket(ticket)
    store[ticket_id] = ticket
    return returned


def get_ticket(store: TicketStore, ticket_id: str) -> Ticket:
    validate_uuid(ticket_id)
    validated = validate_store(store)
    if ticket_id not in validated:
        raise TicketNotFoundError(f"Ticket {ticket_id} was not found")
    return validated[ticket_id]
