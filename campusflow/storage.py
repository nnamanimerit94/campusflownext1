"""Versioned JSON persistence for a single local writer."""

import json
import os
from pathlib import Path
import tempfile

from campusflow.models import StorageError, TicketStore, ValidationError, validate_store, validate_ticket


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValidationError(f"Nonstandard JSON constant: {value}")


def load_tickets(path: Path) -> TicketStore:
    """Load validated records; missing files alone represent an empty store."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise StorageError(f"Could not read ticket file: {path}") from exc

    try:
        if not isinstance(data, dict) or set(data) != {"schema_version", "tickets"}:
            raise ValidationError("Expected schema_version and tickets envelope")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValidationError("Unsupported schema_version; expected integer 1")
        if not isinstance(data["tickets"], list):
            raise ValidationError("tickets must be a list")
        result: TicketStore = {}
        for record in data["tickets"]:
            ticket = validate_ticket(record)
            if ticket["id"] in result:
                raise ValidationError("Duplicate ticket ID")
            result[ticket["id"]] = ticket
        return result
    except ValidationError as exc:
        raise StorageError(f"Invalid ticket file schema: {path}") from exc


def save_tickets(path: Path, store: TicketStore) -> None:
    """Validate then flush/fsync a sibling temporary file before replacement.

    The parent must exist. No locks, multi-writer coordination or power-loss
    recovery are provided. Replacement is the publication point.
    """
    temporary: Path | None = None
    try:
        validated = validate_store(store)
        payload = json.dumps({"schema_version": 1, "tickets": list(validated.values())},
                             ensure_ascii=True, allow_nan=False, indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as file:
            temporary = Path(file.name)
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except (OSError, UnicodeError, ValidationError, RecursionError) as exc:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as cleanup_error:
                exc.add_note(f"Could not clean temporary file {temporary}: {cleanup_error}")
        raise StorageError(f"Could not save ticket file: {path}") from exc
