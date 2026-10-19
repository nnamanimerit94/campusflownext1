"""Structured follow-up notes with validation before publication."""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from campusflow.models import (
    InvalidTransitionError, Note, TicketStore, ValidationError, clean_text,
    parse_timestamp, validate_ticket, validate_uuid,
)
from campusflow.tickets import get_ticket


def add_note(store: TicketStore, ticket_id: str, *, author: str, body: str) -> Note:
    """Append to an active ticket atomically; return an independent note copy."""
    ticket = get_ticket(store, ticket_id)
    author = clean_text(author, "author", 120)
    body = clean_text(body, "body", 5000)
    if ticket["status"] not in ("open", "in_progress"):
        raise InvalidTransitionError("Reopen resolved or closed tickets before adding notes")

    existing_ids = {note["id"] for note in ticket["notes"]}
    # Same policy as ticket allocation: initial candidate plus ten retries.
    for _ in range(11):
        note_id = validate_uuid(str(uuid4()))
        if note_id not in existing_ids:
            break
    else:
        raise ValidationError("Could not allocate a unique note ID after ten retries")

    timestamp = max(datetime.now(timezone.utc), parse_timestamp(ticket["updated_at"]))
    note: Note = {"id": note_id, "author": author, "body": body,
                  "created_at": timestamp.isoformat()}
    ticket["notes"].append(note)
    ticket["updated_at"] = note["created_at"]
    # Stage and validate a full copy before the single store mutation.
    validated = validate_ticket(ticket)
    returned = deepcopy(validated["notes"][-1])
    store[ticket_id] = validated
    return returned
