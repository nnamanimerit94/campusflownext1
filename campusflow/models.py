"""Shared JSON-compatible contracts and side-effect-free validation."""

from copy import deepcopy
from datetime import datetime, timedelta
from typing import TypedDict, cast
from uuid import UUID


class ValidationError(ValueError):
    """Input does not satisfy the agreed data contract."""


class TicketNotFoundError(LookupError):
    """A valid ticket ID is absent from the store."""


class InvalidTransitionError(ValueError):
    """An operation is not permitted in the current ticket state."""


class StorageError(Exception):
    """Reserved shared error for the separately implemented storage module."""


class Note(TypedDict):
    id: str
    author: str
    body: str
    created_at: str


class Ticket(TypedDict):
    id: str
    student_id: str
    student_name: str
    title: str
    description: str
    category: str
    urgency: str
    affected_users: int
    priority: str
    status: str
    assigned_to: str | None
    created_at: str
    updated_at: str
    notes: list[Note]


TicketStore = dict[str, Ticket]
CATEGORIES = ("payment", "attendance", "technical", "welfare", "other")
URGENCIES = ("low", "medium", "high")
PRIORITIES = (*URGENCIES, "critical")
STATUSES = ("open", "in_progress", "resolved", "closed")
TEXT_LIMITS = {"student_id": 100, "student_name": 120, "title": 200, "description": 5000}


def clean_text(value: object, field: str, limit: int) -> str:
    """Normalize user-entered text; schema validation requires canonical text."""
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValidationError(f"{field} must be nonempty text of at most {limit} characters")
    return value.strip()


def validate_enum(value: object, field: str, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValidationError(f"{field} must be one of {', '.join(allowed)}")
    return value


def validate_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("ID must be a canonical lowercase UUID4 string")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValidationError("ID must be a canonical lowercase UUID4 string") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValidationError("ID must be a canonical lowercase UUID4 string")
    return value


def priority_for(urgency: object, affected_users: object) -> str:
    """Shared derivation used by creation and persisted-schema validation."""
    urgency = validate_enum(urgency, "urgency", URGENCIES)
    if type(affected_users) is not int or affected_users < 1:
        raise ValidationError("affected_users must be a positive integer (not bool)")
    return PRIORITIES[URGENCIES.index(urgency) + (affected_users >= 10)]


def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise ValidationError("Timestamp must be a timezone-aware UTC ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Invalid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValidationError("Timestamp must use UTC")
    return parsed


def _record(value: object, fields: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValidationError(f"{name} must contain exactly the documented fields")
    return value


def _canonical_text(value: object, field: str, limit: int) -> None:
    if clean_text(value, field, limit) != value:
        raise ValidationError(f"{field} must be stripped")


def validate_ticket(ticket: object) -> Ticket:
    """Validate the complete record and return an independent deep copy."""
    data = _record(ticket, set(Ticket.__annotations__), "Ticket")
    validate_uuid(data["id"])
    for field, limit in TEXT_LIMITS.items():
        _canonical_text(data[field], field, limit)
    validate_enum(data["category"], "category", CATEGORIES)
    expected_priority = priority_for(data["urgency"], data["affected_users"])
    if data["priority"] != expected_priority:
        raise ValidationError("priority must match urgency and affected_users")
    status = validate_enum(data["status"], "status", STATUSES)
    if data["assigned_to"] is not None:
        _canonical_text(data["assigned_to"], "assigned_to", 120)
    elif status != "open":
        raise ValidationError("Active work and completed tickets require an assignee")
    created = parse_timestamp(data["created_at"])
    updated = parse_timestamp(data["updated_at"])
    if updated < created:
        raise ValidationError("updated_at cannot precede created_at")
    if not isinstance(data["notes"], list):
        raise ValidationError("notes must be a list")
    seen = set()
    for value in data["notes"]:
        note = _record(value, set(Note.__annotations__), "Note")
        note_id = validate_uuid(note["id"])
        if note_id in seen:
            raise ValidationError("Duplicate note ID")
        seen.add(note_id)
        _canonical_text(note["author"], "author", 120)
        _canonical_text(note["body"], "body", 5000)
        if not created <= parse_timestamp(note["created_at"]) <= updated:
            raise ValidationError("Note timestamp must be within the ticket's time range")
    return cast(Ticket, deepcopy(data))


def validate_store(value: object) -> TicketStore:
    """Accept an ID-keyed store (not a storage envelope); never mutate it."""
    if not isinstance(value, dict):
        raise ValidationError("Store must be a dictionary keyed by ticket ID")
    result: TicketStore = {}
    for key, ticket in value.items():
        validate_uuid(key)
        validated = validate_ticket(ticket)
        if key != validated["id"]:
            raise ValidationError("Store key must match ticket ID")
        result[key] = validated
    return result
