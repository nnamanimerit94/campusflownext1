# CampusFlow Next

A Python campus helpdesk CLI in development. Python 3.11+; standard library only.

Planning PR #2, foundation PR #4, ticket-core PR #6 and notes PR #8 are merged. This persistence branch adds strict JSON loading and atomic saving; independent review/merge is pending. Lifecycle, search, reports, CLI and Understanding Check remain unimplemented.

Ticket APIs: `campusflow.tickets.create_ticket`, `calculate_priority` and `get_ticket`. Creation takes an ID-keyed store and required student_id, student_name, title, description, category, urgency and affected_users keyword arguments. Counts 1–9 retain urgency; >=10 escalates one tier (high becomes critical). Free text is stripped; enums are exact lowercase. New tickets are open/unassigned with empty notes and equal UTC timestamps. UUID allocation permits an initial candidate plus ten collision retries.

`campusflow.models.validate_ticket` and `validate_store` enforce the complete schema, including nested Note records, and return deep copies. Stored text must already be stripped; validate_store accepts an ID-keyed dictionary, not a storage envelope. Lookup raises ValidationError for malformed IDs and TicketNotFoundError for absent valid IDs. Whole-store validation prioritizes integrity over large-store lookup speed. Rejected operations preserve the store; returned objects do not alias it. Ticket and note operations remain in memory; storage calls are explicit.

## Run the tests
From the repository root (no dependency installation required):

```sh
python scripts/run_tests.py
```

On Windows use `py` instead of `python` if needed. The runner discovers `tests/test_*.py`, rejects zero discovered tests and exits nonzero for failures/import errors. For direct discovery: `python -m unittest discover -s tests -v` (without the empty-suite guard).

GitHub Actions runs the guarded command for every pull request and pushes to main on Python 3.11 and 3.14. No application run command exists yet.

## Structure
- `campusflow/`: application package; domain modules arrive in later reviewed PRs.
- `tests/`: unittest suite.
- `scripts/run_tests.py`: local/CI runner.
- `.github/workflows/tests.yml`: CI matrix.
- `docs/PROGRESS.md`: delivery and verification evidence.

See [ENGINEERING_PLAN.md](ENGINEERING_PLAN.md) for approved contracts and ownership, [AGENTS.md](AGENTS.md) for collaboration rules, and [foundation issue #3](https://github.com/nnamanimerit94/campusflownext1/issues/3).


## Structured notes
Use `campusflow.notes.add_note(store, ticket_id, author="Mentor", body="Update")`. Author/body are stripped, nonempty, and limited to 120/5000 characters. Only open/in_progress tickets accept notes; resolved/closed tickets must be reopened first. Each note has a canonical UUID4 unique within its ticket (initial candidate plus ten collision retries). Note time and updated_at use max(current UTC, previous updated_at). Existing notes and unrelated ticket fields are preserved; validation failures leave the store unchanged, and the returned Note is a deep copy. Persistence is available through the explicit storage API below on this branch.


## JSON persistence (this branch)
Use `storage.load_tickets(Path("tickets.json"))` and `storage.save_tickets(Path("tickets.json"), store)` from `campusflow.storage`. The parent folder must already exist. The UTF-8 JSON envelope contains exactly schema_version (integer 1) and tickets (list). Missing files return an empty store; empty/corrupt/unsupported/schema-invalid files raise StorageError without altering the file. Duplicate ticket IDs, object keys, note IDs and nonstandard JSON constants are rejected. Errors preserve their original cause.

Save validates the entire store, writes a sibling temporary file, flushes/fsyncs and closes it, then calls os.replace. Failures before replacement preserve the old destination and attempt temporary-file cleanup; cleanup failures are included on the original exception. Replacement may change file permissions to those of the temporary file. No concurrent writers, file locking, parent creation, legacy migration or guaranteed hardware/power-loss recovery. Callers must report failures rather than treating them as an empty database.


## Ticket assignment and lifecycle (Engineer B PR)
Use `assign_ticket(store, ticket_id, assignee)`, `transition_ticket(store, ticket_id, new_status)` and `reopen_ticket(store, ticket_id)` from `campusflow.workflow`. Assign or reassign only active tickets; transition open→in_progress (requires assignee), in_progress→resolved, resolved→closed. Reopen resolved/closed through the explicit API. Invalid transitions leave the store untouched. Successful operations preserve history, use nondecreasing UTC timestamps and return independent copies. This module awaits independent Engineer A review and merge.

## Search and combined filters (Engineer B PR)
`campusflow.search.search_tickets(store, *, query='', status=None, priority=None, category=None, assigned_to=None)` performs stripped casefold substring search across ticket ID, student ID/name, title, description and note bodies. Optional enum and assignee filters combine with AND; assignee comparison is case-insensitive exact match. Results are deep-copy snapshots ordered by UTC creation time then ID. Invalid filters or stores raise ValidationError without mutation. Search is awaiting independent Engineer A review and merge; reports/CLI are not part of this PR.

## Current-state reports (Engineer B PR)
`campusflow.reports.ticket_statistics(store)` returns `total`, `by_status`, `by_priority`, `by_category` and `unassigned` for the current validated ticket store. Every approved enum value appears, including zero-count buckets and critical priority. Reopened tickets count by current status, not past resolution events. Reports never mutate the store. This branch awaits independent Engineer A review/merge; search PR #14 is separate.
