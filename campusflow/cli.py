"""Interactive, single-operator CLI with save-before-publish mutations."""

from copy import deepcopy
from pathlib import Path

from campusflow.models import ValidationError, TicketNotFoundError, InvalidTransitionError, StorageError
from campusflow.tickets import create_ticket
from campusflow.notes import add_note
from campusflow.workflow import assign_ticket, transition_ticket, reopen_ticket
from campusflow.search import search_tickets
from campusflow.reports import ticket_statistics
from campusflow.storage import load_tickets, save_tickets
from campusflow.understanding import run_check


def main(input_fn=input, output_fn=print, path=None) -> int:
    """Run a local menu. Return nonzero if the initial database cannot be loaded."""
    path = Path("tickets.json") if path is None else Path(path)
    try:
        store = load_tickets(path)
    except StorageError as exc:
        output_fn(f"Cannot load tickets: {exc}. Original file left untouched.")
        return 1

    def ask(prompt):
        return input_fn(prompt).strip()

    def change(operation):
        nonlocal store
        staged = deepcopy(store)
        result = operation(staged)
        save_tickets(path, staged)
        store = staged
        output_fn(f"Saved: {result['id']}")

    actions = {
        "1": "Create ticket", "2": "Assign ticket", "3": "Add note",
        "4": "Start ticket", "5": "Resolve ticket", "6": "Close ticket",
        "7": "Reopen ticket", "8": "Search tickets", "9": "Statistics",
        "10": "Reload from disk", "11": "Understanding Check", "12": "Exit",
    }
    output_fn(f"CampusFlow Next | {path}")
    while True:
        for key, label in actions.items():
            output_fn(f"{key}. {label}")
        try:
            choice = ask("Choose: ")
            if choice == "12":
                output_fn("Goodbye.")
                return 0
            if choice == "1":
                fields = {name: ask(f"{name}: ") for name in (
                    "student_id", "student_name", "title", "description",
                    "category", "urgency", "affected_users")}
                fields["affected_users"] = int(fields["affected_users"])
                change(lambda staged: create_ticket(staged, **fields))
            elif choice == "2":
                ticket_id, assignee = ask("Ticket ID: "), ask("Assignee: ")
                change(lambda staged: assign_ticket(staged, ticket_id, assignee))
            elif choice == "3":
                ticket_id, author, body = ask("Ticket ID: "), ask("Author: "), ask("Note: ")
                change(lambda staged: add_note(staged, ticket_id, author=author, body=body))
            elif choice in ("4", "5", "6"):
                ticket_id = ask("Ticket ID: ")
                status = {"4": "in_progress", "5": "resolved", "6": "closed"}[choice]
                change(lambda staged: transition_ticket(staged, ticket_id, status))
            elif choice == "7":
                ticket_id = ask("Ticket ID: ")
                change(lambda staged: reopen_ticket(staged, ticket_id))
            elif choice == "8":
                query = ask("Search text (blank for all): ")
                status = ask("Status filter (blank for all): ") or None
                priority = ask("Priority filter (blank for all): ") or None
                category = ask("Category filter (blank for all): ") or None
                assignee = ask("Assignee filter (blank for all): ") or None
                matches = search_tickets(store, query=query, status=status,
                                         priority=priority, category=category,
                                         assigned_to=assignee)
                output_fn(f"{len(matches)} ticket(s)")
                for ticket in matches:
                    output_fn(f"{ticket['id']} | {ticket['status']} | {ticket['title']}")
            elif choice == "9":
                output_fn(str(ticket_statistics(store)))
            elif choice == "10":
                refreshed = load_tickets(path)
                store = refreshed
                output_fn(f"Reloaded {len(store)} ticket(s).")
            elif choice == "11":
                run_check(input_fn=input_fn, output_fn=output_fn)
            else:
                output_fn("Unknown menu option.")
        except (EOFError, KeyboardInterrupt):
            output_fn("Input ended; no pending changes saved.")
            return 0
        except (ValidationError, TicketNotFoundError, InvalidTransitionError,
                StorageError, ValueError) as exc:
            output_fn(f"Operation failed; active data unchanged: {exc}")
